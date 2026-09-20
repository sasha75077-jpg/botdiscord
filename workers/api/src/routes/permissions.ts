import { Hono } from 'hono'
import type { Env } from '../index'
import { verifyToken } from './auth'

const permissions = new Hono<{ Bindings: Env }>()

type Caller = { role: string; guild_id?: string; isBot: boolean } | null

async function getCaller(c: any, env: Env): Promise<Caller> {
  const header = c.req.header('Authorization')
  if (!header?.startsWith('Bearer ')) return null
  const token = header.substring(7)
  if (env.SYNC_SECRET && token === env.SYNC_SECRET) {
    return { role: 'bot', isBot: true }
  }
  const payload: any = await verifyToken(token, env.SECRET_KEY)
  if (!payload) return null
  return { role: payload.role as string, guild_id: payload.guild_id as string | undefined, isBot: false }
}

// Роли по иерархии: owner > admin > recruiter > user
function canAssign(callerRole: string, targetRole: string): boolean {
  if (callerRole === 'owner' || callerRole === 'bot') return true
  if (callerRole === 'admin') return targetRole === 'recruiter' || targetRole === 'user'
  return false
}

// GET /guilds/:guildId/permissions
permissions.get('/:guildId/permissions', async (c) => {
  const guildId = c.req.param('guildId')

  const result = await c.env.DB.prepare(
    'SELECT * FROM permissions WHERE guild_id = ? ORDER BY role DESC'
  ).bind(guildId).all()

  return c.json({ permissions: result.results })
})

// POST /guilds/:guildId/permissions (owner: любые; admin: только recruiter/user своего сервера)
permissions.post('/:guildId/permissions', async (c) => {
  const caller = await getCaller(c, c.env)
  if (!caller) {
    return c.json({ error: 'Forbidden' }, 403)
  }

  const guildId = c.req.param('guildId')
  const { discord_id, role, granted_by } = await c.req.json<{ discord_id: string; role: string; granted_by?: string }>()

  if (!discord_id || !['owner', 'admin', 'recruiter', 'user'].includes(role)) {
    return c.json({ error: 'Invalid discord_id or role' }, 400)
  }

  if (!caller.isBot && caller.role !== 'owner' && caller.guild_id !== guildId) {
    return c.json({ error: 'Not an admin of this guild' }, 403)
  }
  if (!canAssign(caller.role, role)) {
    return c.json({ error: 'Only owner can assign this role' }, 403)
  }

  // Кто выдал: из JWT, ключ бота или явно
  let granter: string | null = granted_by || null
  const token = (c.req.header('Authorization') || '').substring(7)
  if (c.env.SYNC_SECRET && token === c.env.SYNC_SECRET) {
    granter = granted_by || 'discord-sync'
  } else {
    const payload: any = await verifyToken(token, c.env.SECRET_KEY)
    granter = granted_by || payload?.discord_id || payload?.email || null
  }

  await c.env.DB.prepare(
    `INSERT INTO permissions (discord_id, guild_id, role, assigned_by)
     VALUES (?, ?, ?, ?)
     ON CONFLICT(discord_id, guild_id) DO UPDATE SET role = ?, assigned_by = ?`
  ).bind(discord_id, guildId, role, granter, role, granter).run()

  return c.json({ message: 'Permission assigned' })
})

// DELETE /guilds/:guildId/permissions/:discordId (?only_synced=1 - только автоназначенные)
// Удалить могут: owner/bot - любые; admin - только recruiter/user своего сервера
permissions.delete('/:guildId/permissions/:discordId', async (c) => {
  const caller = await getCaller(c, c.env)
  if (!caller) {
    return c.json({ error: 'Forbidden' }, 403)
  }

  const guildId = c.req.param('guildId')
  const discordId = c.req.param('discordId')
  const onlySynced = c.req.query('only_synced') === '1'

  const target = await c.env.DB.prepare(
    'SELECT role FROM permissions WHERE discord_id = ? AND guild_id = ?'
  ).bind(discordId, guildId).first<{ role: string }>()

  if (!onlySynced) {
    if (!caller.isBot && caller.role !== 'owner' && caller.guild_id !== guildId) {
      return c.json({ error: 'Not an admin of this guild' }, 403)
    }
    const targetRole = target?.role || 'user'
    if (!canAssign(caller.role, targetRole)) {
      return c.json({ error: 'Only owner can remove this role' }, 403)
    }
  }

  if (onlySynced) {
    await c.env.DB.prepare(
      "DELETE FROM permissions WHERE discord_id = ? AND guild_id = ? AND assigned_by = 'discord-sync'"
    ).bind(discordId, guildId).run()
  } else {
    await c.env.DB.prepare(
      'DELETE FROM permissions WHERE discord_id = ? AND guild_id = ?'
    ).bind(discordId, guildId).run()
  }

  return c.json({ message: 'Permission removed' })
})

// GET /guilds/:guildId/permissions/me
permissions.get('/:guildId/permissions/me', async (c) => {
  const guildId = c.req.param('guildId')
  const authHeader = c.req.header('Authorization')

  if (!authHeader?.startsWith('Bearer ')) {
    return c.json({ error: 'Missing authorization' }, 401)
  }

  // TODO: Extract discord_id from JWT and return role
  return c.json({ message: 'Not implemented' }, 501)
})

export const permissionsRoutes = permissions

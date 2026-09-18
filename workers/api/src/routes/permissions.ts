import { Hono } from 'hono'
import type { Env } from '../index'

const permissions = new Hono<{ Bindings: Env }>()

// GET /guilds/:guildId/permissions
permissions.get('/:guildId/permissions', async (c) => {
  const guildId = c.req.param('guildId')

  const result = await c.env.DB.prepare(
    'SELECT * FROM permissions WHERE guild_id = ? ORDER BY role DESC'
  ).bind(guildId).all()

  return c.json(result.results)
})

// POST /guilds/:guildId/permissions
permissions.post('/:guildId/permissions', async (c) => {
  const guildId = c.req.param('guildId')
  const { discord_id, role } = await c.req.json<{ discord_id: string; role: string }>()

  await c.env.DB.prepare(
    `INSERT INTO permissions (discord_id, guild_id, role)
     VALUES (?, ?, ?)
     ON CONFLICT(discord_id, guild_id) DO UPDATE SET role = ?`
  ).bind(discord_id, guildId, role, role).run()

  return c.json({ message: 'Permission assigned' })
})

// DELETE /guilds/:guildId/permissions/:discordId
permissions.delete('/:guildId/permissions/:discordId', async (c) => {
  const guildId = c.req.param('guildId')
  const discordId = c.req.param('discordId')

  await c.env.DB.prepare(
    'DELETE FROM permissions WHERE discord_id = ? AND guild_id = ?'
  ).bind(discordId, guildId).run()

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

import { Hono } from 'hono'
import type { Env } from '../index'
import { verifyToken } from './auth'

const users = new Hono<{ Bindings: Env }>()

// PUT /guilds/:guildId/users/me - свой static для выгрузки премий
users.put('/:guildId/users/me', async (c) => {
  const header = c.req.header('Authorization')
  if (!header?.startsWith('Bearer ')) {
    return c.json({ error: 'Forbidden' }, 403)
  }
  const payload: any = await verifyToken(header.substring(7), c.env.SECRET_KEY)
  if (!payload?.discord_id) {
    return c.json({ error: 'Forbidden' }, 403)
  }
  const guildId = c.req.param('guildId')
  if (payload.user_type !== 'owner' && payload.guild_id !== guildId) {
    return c.json({ error: 'Forbidden' }, 403)
  }
  const body = await c.req.json<{ static?: string }>()
  const st = String(body.static || '').trim().slice(0, 32)
  await c.env.DB.prepare(
    `INSERT INTO users (discord_id, guild_id, static) VALUES (?, ?, ?)
     ON CONFLICT(discord_id, guild_id) DO UPDATE SET static = ?`
  ).bind(payload.discord_id, guildId, st || null, st || null).run()
  return c.json({ static: st || null })
})

// GET /guilds/:guildId/users/me
users.get('/:guildId/users/me', async (c) => {
  const guildId = c.req.param('guildId')
  const authHeader = c.req.header('Authorization')

  if (!authHeader?.startsWith('Bearer ')) {
    return c.json({ error: 'Missing authorization' }, 401)
  }

  // TODO: Extract discord_id from JWT
  return c.json({ message: 'Not implemented' }, 501)
})

// GET /guilds/:guildId/users/:discordId
users.get('/:guildId/users/:discordId', async (c) => {
  const guildId = c.req.param('guildId')
  const discordId = c.req.param('discordId')

  const user = await c.env.DB.prepare(
    'SELECT * FROM users WHERE discord_id = ? AND guild_id = ?'
  ).bind(discordId, guildId).first()

  if (!user) {
    return c.json({ error: 'User not found' }, 404)
  }

  return c.json(user)
})

// GET /guilds/:guildId/users/
users.get('/:guildId/users/', async (c) => {
  const guildId = c.req.param('guildId')

  const result = await c.env.DB.prepare(
    'SELECT * FROM users WHERE guild_id = ? ORDER BY created_at DESC'
  ).bind(guildId).all()

  return c.json(result.results)
})

export const usersRoutes = users

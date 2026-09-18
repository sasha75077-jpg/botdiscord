import { Hono } from 'hono'
import type { Env } from '../index'

const users = new Hono<{ Bindings: Env }>()

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

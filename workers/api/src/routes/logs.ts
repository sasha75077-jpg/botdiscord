import { Hono } from 'hono'
import type { Env } from '../index'

const logs = new Hono<{ Bindings: Env }>()

// GET /guilds/:guildId/bot-logs - журнал ошибок бота для овнера
logs.get('/:guildId/bot-logs', async (c) => {
  const guildId = c.req.param('guildId')
  const limit = Math.min(parseInt(c.req.query('limit') || '100', 10) || 100, 500)

  const result = await c.env.DB.prepare(
    'SELECT * FROM bot_logs WHERE guild_id = ? ORDER BY created_at DESC LIMIT ?'
  ).bind(guildId, limit).all()

  return c.json({ logs: result.results })
})

// POST /guilds/:guildId/bot-logs - пишет только бот (SYNC_SECRET)
logs.post('/:guildId/bot-logs', async (c) => {
  const key = c.env.SYNC_SECRET
  const token = (c.req.header('Authorization') || '').substring(7)
  if (!key || token !== key) {
    return c.json({ error: 'Forbidden' }, 403)
  }

  const guildId = c.req.param('guildId')
  const { level, source, message } = await c.req.json<{
    level?: string; source?: string; message: string
  }>()

  if (!message) {
    return c.json({ error: 'Missing message' }, 400)
  }

  await c.env.DB.prepare(
    'INSERT INTO bot_logs (guild_id, level, source, message) VALUES (?, ?, ?, ?)'
  ).bind(guildId, level || 'error', source || null, message).run()

  return c.json({ message: 'Logged' })
})

export const logsRoutes = logs

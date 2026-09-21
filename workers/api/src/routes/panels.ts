import { Hono } from 'hono'
import type { Env } from '../index'
import { verifyToken } from './auth'

const panels = new Hono<{ Bindings: Env }>()

async function isAdmin(c: any, env: Env): Promise<boolean> {
  const header = c.req.header('Authorization')
  if (!header?.startsWith('Bearer ')) return false
  const payload: any = await verifyToken(header.substring(7), env.SECRET_KEY)
  return payload?.role === 'owner' || payload?.role === 'admin'
}

function isBot(c: any, env: Env): boolean {
  const token = (c.req.header('Authorization') || '').substring(7)
  return !!env.SYNC_SECRET && token === env.SYNC_SECRET
}

// POST /panels/tasks - поставить постинг панели (admin/owner)
panels.post('/tasks', async (c) => {
  if (!(await isAdmin(c, c.env))) return c.json({ error: 'Forbidden' }, 403)
  const body = await c.req.json<{ guild_id?: string; panel_type?: string; channel_id?: string }>()
  if (!body.guild_id || !['admin_hub', 'profile'].includes(body.panel_type || '') || !body.channel_id) {
    return c.json({ error: 'Нужно guild_id, panel_type, channel_id' }, 400)
  }
  const header = c.req.header('Authorization') || ''
  const payload: any = await verifyToken(header.substring(7), c.env.SECRET_KEY)
  if (payload?.role !== 'owner' && payload?.guild_id !== body.guild_id) {
    return c.json({ error: 'Forbidden' }, 403)
  }
  const res = await c.env.DB.prepare(
    'INSERT INTO panel_tasks (guild_id, panel_type, channel_id, created_by) VALUES (?, ?, ?, ?)'
  ).bind(body.guild_id, body.panel_type, body.channel_id,
    payload?.discord_id || payload?.email || null).run()
  return c.json({ id: res.meta.last_row_id })
})

// GET /panels/tasks - очередь/история (admin/owner)
panels.get('/tasks', async (c) => {
  if (!(await isAdmin(c, c.env))) return c.json({ error: 'Forbidden' }, 403)
  const guildId = c.req.query('guild_id')
  const result = guildId
    ? await c.env.DB.prepare('SELECT * FROM panel_tasks WHERE guild_id = ? ORDER BY id DESC LIMIT 50').bind(guildId).all()
    : await c.env.DB.prepare('SELECT * FROM panel_tasks ORDER BY id DESC LIMIT 50').all()
  return c.json({ tasks: result.results })
})

// GET /panels/tasks/pending - забирает бот (SYNC_SECRET)
panels.get('/tasks/pending', async (c) => {
  if (!isBot(c, c.env)) return c.json({ error: 'Forbidden' }, 403)
  const result = await c.env.DB.prepare(
    "SELECT * FROM panel_tasks WHERE status = 'pending' ORDER BY id ASC LIMIT 20"
  ).all()
  return c.json(result.results)
})

// PUT /panels/tasks/:id - результат от бота (SYNC_SECRET)
panels.put('/tasks/:id', async (c) => {
  if (!isBot(c, c.env)) return c.json({ error: 'Forbidden' }, 403)
  const body = await c.req.json<{ status?: string; result?: string }>()
  if (!['done', 'error'].includes(body.status || '')) {
    return c.json({ error: 'Bad status' }, 400)
  }
  await c.env.DB.prepare(
    'UPDATE panel_tasks SET status = ?, result = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?'
  ).bind(body.status, body.result || null, c.req.param('id')).run()
  return c.json({ ok: true })
})

export const panelsRoutes = panels

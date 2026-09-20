import { Hono } from 'hono'
import type { Env } from '../index'
import { verifyToken } from './auth'

const showcase = new Hono<{ Bindings: Env }>()

async function isOwner(c: any, env: Env): Promise<boolean> {
  const header = c.req.header('Authorization')
  if (!header?.startsWith('Bearer ')) return false
  const payload: any = await verifyToken(header.substring(7), env.SECRET_KEY)
  return payload?.role === 'owner'
}

// GET /showcase - публичная витрина (?all=1 для овнера - включая скрытые)
showcase.get('/', async (c) => {
  let mine: any = null
  const header = c.req.header('Authorization')
  if (header?.startsWith('Bearer ')) {
    mine = await verifyToken(header.substring(7), c.env.SECRET_KEY)
  }
  const showAll = c.req.query('all') === '1' && (mine as any)?.role === 'owner'
  const result = showAll
    ? await c.env.DB.prepare(
      'SELECT * FROM showcase_servers ORDER BY sort_order ASC, id ASC'
    ).all()
    : await c.env.DB.prepare(
      'SELECT * FROM showcase_servers WHERE is_active = 1 ORDER BY sort_order ASC, id ASC'
    ).all()

  const items = await Promise.all(
    result.results.map(async (s: any) => {
      let memberCount: number | null = null
      let guildName: string | null = null
      if (s.guild_id && c.env.DISCORD_BOT_TOKEN) {
        try {
          const resp = await fetch(
            `${c.env.DISCORD_API_ENDPOINT}/guilds/${s.guild_id}?with_counts=true`,
            { headers: { Authorization: `Bot ${c.env.DISCORD_BOT_TOKEN}` } }
          )
          if (resp.ok) {
            const g = await resp.json<{ approximate_member_count?: number; name?: string }>()
            memberCount = g.approximate_member_count ?? null
            guildName = g.name ?? null
          }
        } catch { /* ignore */ }
      }
      return { ...s, member_count: memberCount, guild_name: guildName };
    })
  )
  return c.json({ servers: items })
})

// POST /showcase - только овнер
showcase.post('/', async (c) => {
  if (!(await isOwner(c, c.env))) return c.json({ error: 'Forbidden' }, 403)
  const body = await c.req.json<{
    guild_id?: string; title: string; description?: string;
    majestic_server?: string; invite_url: string; sort_order?: number;
  }>()
  if (!body.title || !body.invite_url) {
    return c.json({ error: 'Нужно название и ссылка-приглашение' }, 400)
  }
  const res = await c.env.DB.prepare(
    `INSERT INTO showcase_servers (guild_id, title, description, majestic_server, invite_url, sort_order)
     VALUES (?, ?, ?, ?, ?, ?)`
  ).bind(body.guild_id || null, body.title, body.description || null,
    body.majestic_server || null, body.invite_url, body.sort_order ?? 0).run()
  return c.json({ id: res.meta.last_row_id })
})

// PUT /showcase/:id - только овнер
showcase.put('/:id', async (c) => {
  if (!(await isOwner(c, c.env))) return c.json({ error: 'Forbidden' }, 403)
  const id = c.req.param('id')
  const body = await c.req.json<{
    guild_id?: string; title?: string; description?: string;
    majestic_server?: string; invite_url?: string; sort_order?: number; is_active?: number;
  }>()
  await c.env.DB.prepare(
    `UPDATE showcase_servers SET
       guild_id = COALESCE(?, guild_id), title = COALESCE(?, title),
       description = COALESCE(?, description), majestic_server = COALESCE(?, majestic_server),
       invite_url = COALESCE(?, invite_url), sort_order = COALESCE(?, sort_order),
       is_active = COALESCE(?, is_active), updated_at = CURRENT_TIMESTAMP
     WHERE id = ?`
  ).bind(body.guild_id ?? null, body.title ?? null, body.description ?? null,
    body.majestic_server ?? null, body.invite_url ?? null,
    body.sort_order ?? null, body.is_active ?? null, id).run()
  return c.json({ ok: true })
})

// DELETE /showcase/:id - только овнер
showcase.delete('/:id', async (c) => {
  if (!(await isOwner(c, c.env))) return c.json({ error: 'Forbidden' }, 403)
  await c.env.DB.prepare('DELETE FROM showcase_servers WHERE id = ?')
    .bind(c.req.param('id')).run()
  return c.json({ ok: true })
})

export const showcaseRoutes = showcase

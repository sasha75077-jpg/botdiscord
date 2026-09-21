import { Hono } from 'hono'
import type { Env } from '../index'
import { verifyToken } from './auth'

const ranks = new Hono<{ Bindings: Env }>()

async function isStaff(c: any, env: Env, guildId?: string): Promise<boolean> {
  const header = c.req.header('Authorization')
  if (!header?.startsWith('Bearer ')) return false
  const token = header.substring(7)
  if (env.SYNC_SECRET && token === env.SYNC_SECRET) return true
  const payload: any = await verifyToken(token, env.SECRET_KEY)
  if (!payload) return false
  if (payload.role === 'owner' || payload.role === 'admin') {
    return payload.role === 'owner' || payload.guild_id === guildId
  }
  return false
}

// GET /guilds/:guildId/ranks - лестница рангов (открыто)
ranks.get('/:guildId/ranks', async (c) => {
  const guildId = c.req.param('guildId')
  const rows = await c.env.DB.prepare(
    'SELECT * FROM ranks WHERE guild_id = ? ORDER BY sort_order ASC'
  ).bind(guildId).all()
  return c.json({ ranks: rows.results })
})

// POST /guilds/:guildId/ranks - новый ранг (admin/owner)
ranks.post('/:guildId/ranks', async (c) => {
  const guildId = c.req.param('guildId')
  if (!(await isStaff(c, c.env, guildId))) return c.json({ error: 'Forbidden' }, 403)
  const body = await c.req.json<{ name?: string; role_id?: string; sort_order?: number }>()
  if (!body.name?.trim()) return c.json({ error: 'Нужно название' }, 400)
  const res = await c.env.DB.prepare(
    'INSERT INTO ranks (name, role_id, sort_order, guild_id) VALUES (?, ?, ?, ?)'
  ).bind(body.name.trim(), body.role_id || null, body.sort_order ?? 0, guildId).run()
  return c.json({ id: res.meta.last_row_id })
})

// PUT /guilds/:guildId/ranks/:id - привязка роли/порядок (admin/owner)
ranks.put('/:guildId/ranks/:id', async (c) => {
  const guildId = c.req.param('guildId')
  if (!(await isStaff(c, c.env, guildId))) return c.json({ error: 'Forbidden' }, 403)
  const body = await c.req.json<{ name?: string; role_id?: string | null; sort_order?: number }>()
  await c.env.DB.prepare(
    `UPDATE ranks SET name = COALESCE(?, name), role_id = ?,
       sort_order = COALESCE(?, sort_order) WHERE id = ? AND guild_id = ?`
  ).bind(body.name || null, body.role_id ?? null, body.sort_order ?? null,
    c.req.param('id'), guildId).run()
  return c.json({ ok: true })
})

// DELETE /guilds/:guildId/ranks/:id - удалить ранг (owner)
ranks.delete('/:guildId/ranks/:id', async (c) => {
  const header = c.req.header('Authorization')
  if (!header?.startsWith('Bearer ')) return c.json({ error: 'Forbidden' }, 403)
  const payload: any = await verifyToken(header.substring(7), c.env.SECRET_KEY)
  if (!payload || payload.role !== 'owner') return c.json({ error: 'Forbidden' }, 403)
  await c.env.DB.prepare('DELETE FROM ranks WHERE id = ? AND guild_id = ?')
    .bind(c.req.param('id'), c.req.param('guildId')).run()
  return c.json({ ok: true })
})

// GET /guilds/:guildId/requirements - требования main+alt
ranks.get('/:guildId/requirements', async (c) => {
  const main = await c.env.DB.prepare('SELECT * FROM rank_requirements_main').all()
  const alt = await c.env.DB.prepare('SELECT * FROM rank_requirements_alt').all()
  return c.json({ main: main.results, alt: alt.results })
})

// PUT /guilds/:guildId/requirements - требования (admin/owner)
ranks.put('/:guildId/requirements', async (c) => {
  const guildId = c.req.param('guildId')
  if (!(await isStaff(c, c.env, guildId))) return c.json({ error: 'Forbidden' }, 403)
  const body = await c.req.json<{
    main?: Array<{ rank_from: number; rank_to: number; family_contracts: number }>;
    alt?: Array<{ rank_from: number; rank_to: number; family_contracts: number; tuning_contracts: number }>;
  }>()
  const batch: any[] = []
  for (const r of body.main || []) {
    batch.push(c.env.DB.prepare(
      `INSERT INTO rank_requirements_main (rank_from, rank_to, family_contracts) VALUES (?, ?, ?)
       ON CONFLICT(rank_from, rank_to) DO UPDATE SET family_contracts = ?`
    ).bind(r.rank_from, r.rank_to, r.family_contracts, r.family_contracts))
  }
  for (const r of body.alt || []) {
    batch.push(c.env.DB.prepare(
      `INSERT INTO rank_requirements_alt (rank_from, rank_to, family_contracts, tuning_contracts, system_type)
       VALUES (?, ?, ?, ?, 'main')
       ON CONFLICT(rank_from, rank_to) DO UPDATE SET family_contracts = ?, tuning_contracts = ?`
    ).bind(r.rank_from, r.rank_to, r.family_contracts, r.tuning_contracts,
      r.family_contracts, r.tuning_contracts))
  }
  for (let i = 0; i < batch.length; i += 50) {
    await c.env.DB.batch(batch.slice(i, i + 50))
  }
  return c.json({ ok: true })
})

export const ranksRoutes = ranks

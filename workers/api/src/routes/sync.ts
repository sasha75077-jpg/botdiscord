import { Hono } from 'hono'
import type { Env } from '../index'

const sync = new Hono<{ Bindings: Env }>()

function checkKey(c: any, env: Env): boolean {
  const key = env.SYNC_SECRET
  const token = (c.req.header('Authorization') || '').substring(7)
  return !!key && token === key
}

function mapStatus(s: string | undefined, extra: Record<string, string> = {}): string {
  const v = (s || 'PENDING').toUpperCase()
  if (v === 'APPROVED' || v === 'ACCEPTED') return 'approved'
  if (v === 'REJECTED') return 'rejected'
  if (extra[v]) return extra[v]
  return 'pending'
}

// POST /guilds/:guildId/applications/sync - upsert заявки по external_id (uuid бота)
sync.post('/:guildId/applications/sync', async (c) => {
  if (!checkKey(c, c.env)) return c.json({ error: 'Forbidden' }, 403)
  const guildId = c.req.param('guildId')
  const body = await c.req.json<{
    external_id: string; discord_id: string; status?: string; reason?: string;
    claimed_by?: string; decided_by?: string; thread_id?: string;
    log_channel_id?: string; log_message_id?: string;
  }>()
  if (!body.external_id || !body.discord_id) {
    return c.json({ error: 'Missing external_id or discord_id' }, 400)
  }
  const status = mapStatus(body.status, { CLAIMED: 'pending', NEW: 'pending', TAKEN: 'pending' })

  const existing: any = await c.env.DB.prepare(
    'SELECT * FROM applications WHERE external_id = ?'
  ).bind(body.external_id).first()

  if (existing) {
    await c.env.DB.prepare(
      `UPDATE applications SET status = ?, admin_notes = ?,
        claimed_by = COALESCE(?, claimed_by), decided_by = COALESCE(?, decided_by),
        thread_id = COALESCE(?, thread_id),
        log_channel_id = COALESCE(?, log_channel_id),
        log_message_id = COALESCE(?, log_message_id),
        updated_at = CURRENT_TIMESTAMP WHERE id = ?`
    ).bind(status, body.reason || existing.admin_notes,
      body.claimed_by || null, body.decided_by || null,
      body.thread_id || null, body.log_channel_id || null, body.log_message_id || null,
      existing.id).run()
    return c.json({ id: existing.id, updated: true })
  }
  const res = await c.env.DB.prepare(
    'INSERT INTO applications (external_id, guild_id, discord_id, status, admin_notes) VALUES (?, ?, ?, ?, ?)'
  ).bind(body.external_id, guildId, body.discord_id, status, body.reason || null).run()
  return c.json({ id: res.meta.last_row_id, created: true })
})

// POST /guilds/:guildId/bonus-reports/sync - upsert премии по external_id (report_id бота)
sync.post('/:guildId/bonus-reports/sync', async (c) => {
  if (!checkKey(c, c.env)) return c.json({ error: 'Forbidden' }, 403)
  const guildId = c.req.param('guildId')
  const body = await c.req.json<{
    external_id: string; discord_id: string; amount?: number; status?: string; reason?: string
  }>()
  if (!body.external_id || !body.discord_id) {
    return c.json({ error: 'Missing external_id or discord_id' }, 400)
  }
  const status = mapStatus(body.status, { NEW: 'pending', TAKEN: 'pending' })

  const existing = await c.env.DB.prepare(
    'SELECT id FROM bonus_reports WHERE external_id = ?'
  ).bind(body.external_id).first<{ id: number }>()

  if (existing) {
    await c.env.DB.prepare(
      'UPDATE bonus_reports SET amount = ?, status = ?, reason = ? WHERE id = ?'
    ).bind(body.amount ?? 0, status, body.reason || null, existing.id).run()
    return c.json({ id: existing.id, updated: true })
  }
  const res = await c.env.DB.prepare(
    `INSERT INTO bonus_reports (external_id, guild_id, reporter_discord_id, recipient_discord_id, recipient_nickname, bonus_type, amount, status, reason)
     VALUES (?, ?, ?, ?, ?, 'weekly', ?, ?, ?)`
  ).bind(body.external_id, guildId, body.discord_id, body.discord_id, body.discord_id, body.amount ?? 0, status, body.reason || null).run()
  return c.json({ id: res.meta.last_row_id, created: true })
})

// POST /guilds/:guildId/promotion-reports/sync - upsert повышения по external_id
sync.post('/:guildId/promotion-reports/sync', async (c) => {
  if (!checkKey(c, c.env)) return c.json({ error: 'Forbidden' }, 403)
  const guildId = c.req.param('guildId')
  const body = await c.req.json<{
    external_id: string; discord_id: string; from_rank?: string; to_rank?: string; status?: string; reason?: string
  }>()
  if (!body.external_id || !body.discord_id) {
    return c.json({ error: 'Missing external_id or discord_id' }, 400)
  }
  const status = mapStatus(body.status, { NEW: 'pending', TAKEN: 'pending' })

  const existing = await c.env.DB.prepare(
    'SELECT id FROM promotion_reports WHERE external_id = ?'
  ).bind(body.external_id).first<{ id: number }>()

  if (existing) {
    await c.env.DB.prepare(
      'UPDATE promotion_reports SET status = ?, reason = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?'
    ).bind(status, body.reason || null, existing.id).run()
    return c.json({ id: existing.id, updated: true })
  }
  const res = await c.env.DB.prepare(
    'INSERT INTO promotion_reports (external_id, guild_id, discord_id, from_rank, to_rank, status, reason) VALUES (?, ?, ?, ?, ?, ?, ?)'
  ).bind(body.external_id, guildId, body.discord_id, body.from_rank || null, body.to_rank || null, status, body.reason || null).run()
  return c.json({ id: res.meta.last_row_id, created: true })
})

export const syncRoutes = sync

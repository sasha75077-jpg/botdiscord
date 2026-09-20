import { Hono } from 'hono'
import type { Env } from '../index'

const contracts = new Hono<{ Bindings: Env }>()

// GET /guilds/:guildId/contracts/
contracts.get('/:guildId/contracts/', async (c) => {
  const guildId = c.req.param('guildId')
  const status = c.req.query('status')
  const contractType = c.req.query('contract_type')

  let query = 'SELECT * FROM contracts WHERE guild_id = ?'
  const params: any[] = [guildId]

  if (status) {
    query += ' AND status = ?'
    params.push(status)
  }

  if (contractType) {
    query += ' AND contract_type = ?'
    params.push(contractType)
  }

  query += ' ORDER BY created_at DESC'

  const result = await c.env.DB.prepare(query).bind(...params).all()
  return c.json(result.results)
})

// POST /guilds/:guildId/contracts/sync - upsert от Discord-бота (по природному ключу).
// Auth: Authorization: Bearer <SYNC_SECRET>
contracts.post('/:guildId/contracts/sync', async (c) => {
  const key = c.env.SYNC_SECRET
  if (!key || c.req.header('Authorization') !== `Bearer ${key}`) {
    return c.json({ error: 'Forbidden' }, 403)
  }

  const guildId = c.req.param('guildId')
  const body = await c.req.json<{
    ts: string; discord_id: string; contract_type: string;
    price?: number; nickname?: string; discord_username?: string; status?: string;
  }>()

  if (!body.ts || !body.discord_id || !body.contract_type) {
    return c.json({ error: 'Missing ts, discord_id or contract_type' }, 400)
  }

  const st = (body.status || 'PENDING').toUpperCase()
  const status = st === 'APPROVED' ? 'approved' : st === 'REJECTED' ? 'rejected' : 'pending'
  const nick = body.nickname || body.discord_id

  await c.env.DB.prepare(
    'INSERT INTO users (discord_id, guild_id, discord_username) VALUES (?, ?, ?) ON CONFLICT(discord_id, guild_id) DO NOTHING'
  ).bind(body.discord_id, guildId, body.discord_username || null).run()

  const existing = await c.env.DB.prepare(
    'SELECT id FROM contracts WHERE guild_id = ? AND created_at = ? AND discord_id = ? AND contract_type = ?'
  ).bind(guildId, body.ts, body.discord_id, body.contract_type).first<{ id: number }>()

  if (existing) {
    await c.env.DB.prepare(
      'UPDATE contracts SET price = ?, nickname = ?, status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?'
    ).bind(body.price ?? 0, nick, status, existing.id).run()
    return c.json({ id: existing.id, updated: true })
  }

  const res = await c.env.DB.prepare(
    'INSERT INTO contracts (guild_id, discord_id, discord_username, contract_type, nickname, price, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)'
  ).bind(guildId, body.discord_id, body.discord_username || null, body.contract_type, nick, body.price ?? 0, status, body.ts).run()
  return c.json({ id: res.meta.last_row_id, created: true })
})

// GET /guilds/:guildId/contracts/stats (must be before :contractId route)
contracts.get('/:guildId/contracts/stats', async (c) => {
  const guildId = c.req.param('guildId')

  const stats = await c.env.DB.prepare(`
    SELECT
      status,
      COUNT(*) as count
    FROM contracts
    WHERE guild_id = ?
    GROUP BY status
  `).bind(guildId).all()

  return c.json(stats.results)
})

// GET /guilds/:guildId/contracts/:contractId
contracts.get('/:guildId/contracts/:contractId', async (c) => {
  const guildId = c.req.param('guildId')
  const contractId = c.req.param('contractId')

  const contract = await c.env.DB.prepare(
    'SELECT * FROM contracts WHERE guild_id = ? AND id = ?'
  ).bind(guildId, contractId).first()

  if (!contract) {
    return c.json({ error: 'Contract not found' }, 404)
  }

  return c.json(contract)
})

// PUT /guilds/:guildId/contracts/:contractId
contracts.put('/:guildId/contracts/:contractId', async (c) => {
  const guildId = c.req.param('guildId')
  const contractId = c.req.param('contractId')
  const data = await c.req.json<any>()

  const updates: string[] = []
  const params: any[] = []

  if (data.status) {
    updates.push('status = ?')
    params.push(data.status)
  }

  if (data.admin_notes) {
    updates.push('admin_notes = ?')
    params.push(data.admin_notes)
  }

  if (updates.length === 0) {
    return c.json({ error: 'No fields to update' }, 400)
  }

  params.push(guildId, contractId)

  await c.env.DB.prepare(
    `UPDATE contracts SET ${updates.join(', ')} WHERE guild_id = ? AND id = ?`
  ).bind(...params).run()

  return c.json({ message: 'Contract updated' })
})

// DELETE /guilds/:guildId/contracts/:contractId
contracts.delete('/:guildId/contracts/:contractId', async (c) => {
  const guildId = c.req.param('guildId')
  const contractId = c.req.param('contractId')

  await c.env.DB.prepare(
    'DELETE FROM contracts WHERE guild_id = ? AND id = ?'
  ).bind(guildId, contractId).run()

  return c.json({ message: 'Contract deleted' })
})

export const contractsRoutes = contracts

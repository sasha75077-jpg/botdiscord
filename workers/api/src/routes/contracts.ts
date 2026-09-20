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

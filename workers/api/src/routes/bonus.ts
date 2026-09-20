import { Hono } from 'hono'
import type { Env } from '../index'
import { verifyToken } from './auth'
import { enrichMany } from './_discord'

const bonus = new Hono<{ Bindings: Env }>()

async function caller(c: any, env: Env) {
  const header = c.req.header('Authorization')
  if (!header?.startsWith('Bearer ')) return null
  const token = header.substring(7)
  if (env.SYNC_SECRET && token === env.SYNC_SECRET) {
    return { role: 'bot' as string, guild_id: undefined as string | undefined, discord_id: undefined as string | undefined }
  }
  const payload: any = await verifyToken(token, env.SECRET_KEY)
  if (!payload) return null
  if (payload.user_type === 'owner') return { role: 'owner', guild_id: undefined, discord_id: undefined }
  return {
    role: (payload.role || 'user') as string,
    guild_id: payload.guild_id as string | undefined,
    discord_id: payload.discord_id as string | undefined,
  }
}

function sameGuild(who: any, guildId: string): boolean {
  return who.role === 'owner' || who.role === 'bot' || who.guild_id === guildId
}

function isStaff(role: string): boolean {
  return role === 'owner' || role === 'bot' || role === 'admin' || role === 'recruiter'
}

// GET /guilds/:guildId/bonus?status=&discord_id=&since= - свои или все (staff)
bonus.get('/:guildId/bonus', async (c) => {
  const guildId = c.req.param('guildId')
  const who = await caller(c, c.env)
  if (!who || !sameGuild(who, guildId)) return c.json({ error: 'Forbidden' }, 403)

  const status = c.req.query('status')
  const since = c.req.query('since')
  const filterDid = c.req.query('discord_id')

  let query = 'SELECT * FROM bonus_reports WHERE guild_id = ?'
  const params: any[] = [guildId]

  if (!isStaff(who.role)) {
    if (!who.discord_id) return c.json({ error: 'Forbidden' }, 403)
    query += ' AND discord_id = ?'
    params.push(who.discord_id)
  } else if (filterDid) {
    query += ' AND discord_id = ?'
    params.push(filterDid)
  }
  if (status) {
    query += ' AND status = ?'
    params.push(status)
  }
  if (since) {
    query += ' AND (created_at >= ? OR updated_at >= ?)'
    params.push(since, since)
  }
  query += ' ORDER BY created_at DESC LIMIT 200'

  const result = await c.env.DB.prepare(query).bind(...params).all()
  const items = await enrichMany(c.env, result.results, 'discord_id')
  return c.json(items)
})

// POST /guilds/:guildId/bonus - подать премию за неделю (draft; сумму считает бот при принятии)
bonus.post('/:guildId/bonus', async (c) => {
  const guildId = c.req.param('guildId')
  const who = await caller(c, c.env)
  if (!who || !who.discord_id || !sameGuild(who, guildId)) {
    return c.json({ error: 'Forbidden' }, 403)
  }

  const body = await c.req.json<{ week_start?: string; week_end?: string }>()
  let { week_start, week_end } = body
  if (!week_start || !week_end) {
    // Текущая неделя Пн-Вс
    const now = new Date()
    const day = (now.getUTCDay() + 6) % 7
    const mon = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() - day))
    const sun = new Date(mon.getTime() + 6 * 86400000)
    week_start = mon.toISOString().slice(0, 10)
    week_end = sun.toISOString().slice(0, 10)
  }

  const dup = await c.env.DB.prepare(
    `SELECT id FROM bonus_reports WHERE guild_id = ? AND discord_id = ?
     AND week_start = ? AND week_end = ? AND status IN ('pending','approved') LIMIT 1`
  ).bind(guildId, who.discord_id, week_start, week_end).first()
  if (dup) return c.json({ error: 'Премия за эту неделю уже подана' }, 409)

  // Какие контракты войдут: approved за неделю
  const contracts = await c.env.DB.prepare(
    `SELECT id, contract_type, price, created_at FROM contracts
     WHERE guild_id = ? AND discord_id = ? AND status = 'approved'
     AND date(created_at) >= date(?) AND date(created_at) <= date(?)`
  ).bind(guildId, who.discord_id, week_start, week_end).all()

  const res = await c.env.DB.prepare(
    `INSERT INTO bonus_reports (guild_id, reporter_discord_id, recipient_discord_id,
      recipient_nickname, bonus_type, amount, reason, status, contracts_json)
     VALUES (?, ?, ?, ?, 'weekly', 0, ?, 'pending', ?)`
  ).bind(guildId, who.discord_id, who.discord_id, who.discord_id,
    `${week_start}..${week_end}`, JSON.stringify(contracts.results)).run()
  const row = await c.env.DB.prepare('SELECT * FROM bonus_reports WHERE id = ?')
    .bind(res.meta.last_row_id).first()
  return c.json(row)
})

export const bonusRoutes = bonus

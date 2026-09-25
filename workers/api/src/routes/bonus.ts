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

function isAdmin(role: string): boolean {
  return role === 'owner' || role === 'bot' || role === 'admin'
}

// Неделя закрыта после понедельника 00:00 МСК (today > week_end)
function weekLocked(weekEnd: string): boolean {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(weekEnd || '')
  if (!m) return false
  const end = Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3]))
  const nowMsk = Date.now() + 3 * 3600000
  const todayStart = new Date(nowMsk)
  todayStart.setUTCHours(0, 0, 0, 0)
  return todayStart.getTime() > end
}

function currentWeek(): { week_start: string; week_end: string } {
  const now = new Date()
  const day = (now.getUTCDay() + 6) % 7
  const mon = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() - day))
  const sun = new Date(mon.getTime() + 6 * 86400000)
  return { week_start: mon.toISOString().slice(0, 10), week_end: sun.toISOString().slice(0, 10) }
}

// Расчет как в боте (v_contract_value): база + надбавки за ранг
async function calcBonus(
  env: Env, guildId: string, discordId: string, weekStart: string, weekEnd: string
): Promise<{ contracts: number; rank: number; tuning: number; total: number }> {
  const prices = await env.DB.prepare('SELECT item_key, price FROM prices').all()
  const pmap: Record<string, number> = {}
  for (const p of prices.results as Array<{ item_key: string; price: number }>) {
    pmap[p.item_key] = Number(p.price || 0)
  }
  // Ранг получателя = максимальный sort_order среди его Discord-ролей
  let rankSort = 0
  try {
    if (env.DISCORD_BOT_TOKEN) {
      const mresp = await fetch(
        `${env.DISCORD_API_ENDPOINT}/guilds/${guildId}/members/${discordId}`,
        { headers: { Authorization: `Bot ${env.DISCORD_BOT_TOKEN}` } }
      )
      if (mresp.ok) {
        const member = await mresp.json<{ roles: string[] }>()
        const ranks = await env.DB.prepare(
          'SELECT role_id, sort_order FROM ranks WHERE guild_id = ?'
        ).bind(guildId).all()
        for (const r of ranks.results as Array<{ role_id: string; sort_order: number }>) {
          if (r.role_id && (member.roles || []).includes(r.role_id)) {
            rankSort = Math.max(rankSort, r.sort_order || 0)
          }
        }
      }
    }
  } catch { /* ignore */ }

  const rows = await env.DB.prepare(
    `SELECT contract_type, price, details FROM contracts
     WHERE guild_id = ? AND discord_id = ? AND status = 'approved'
     AND date(created_at) >= date(?) AND date(created_at) <= date(?)`
  ).bind(guildId, discordId, weekStart, weekEnd).all()

  let contracts = 0
  let rank = 0
  let tuning = 0
  for (const c of rows.results as any[]) {
    const ct = c.contract_type as string
    let det: any = {}
    try {
      det = JSON.parse(c.details || '{}')
    } catch { /* ignore */ }
    const num = (v: any) => Number(v) || 0
    let base = 0
    if (ct === 'активация') base = num(c.price)
    else if (ct === 'ателье') base = num(det.totalUniforms) * (pmap['atelier.uniform'] || 0)
    else if (ct === 'металлургия-сдача') {
      const oreMap: Record<string, string> = {
        'Железная руда': 'ore.delivery.iron', 'Серебряная руда': 'ore.delivery.silver',
        'Медная руда': 'ore.delivery.copper', 'Оловянная руда': 'ore.delivery.tin',
        'Золотая руда': 'ore.delivery.gold',
      }
      base = pmap[oreMap[det.oreType] || ''] || 0
    } else if (ct === 'металлургия-добыча') {
      base = num(det.iron) * (pmap['ore_unit:iron'] || 0)
        + num(det.silver) * (pmap['ore_unit:silver'] || 0)
        + num(det.copper) * (pmap['ore_unit:copper'] || 0)
        + num(det.tin) * (pmap['ore_unit:tin'] || 0)
        + num(det.gold) * (pmap['ore_unit:gold'] || 0)
    } else if (ct === 'товары') base = 0
    else if (ct === 'агитации-маркетплейс') base = (det.links || []).length * (pmap['agit:marketplace_link'] || 0)
    else if (ct === 'агитации-wn') base = 0
    else if (ct === 'тюнинг') base = pmap['tuning:with_screenshot'] || 0
    else if (ct === 'курьер-еды') base = pmap['courier:delivery'] || 0
    contracts += base
    if (ct === 'товары' || ct === 'металлургия-сдача') rank += rankSort * 1000
    if (ct === 'тюнинг' || ct === 'курьер-еды') tuning += rankSort * 100
  }
  return { contracts, rank, tuning, total: contracts + rank + tuning }
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
  if (!who) return c.json({ error: 'Сессия истекла, войди заново' }, 401)
  if (!who.discord_id) return c.json({ error: 'Подача только через Discord-вход' }, 403)
  if (!sameGuild(who, guildId)) return c.json({ error: 'Forbidden' }, 403)

  const body = await c.req.json<{ week_start?: string; week_end?: string }>()
  let { week_start, week_end } = body
  const cur = currentWeek()
  if (!week_start || !week_end) {
    week_start = cur.week_start
    week_end = cur.week_end
  }
  // Премия собирается только за текущую неделю
  if (week_start !== cur.week_start || week_end !== cur.week_end) {
    return c.json({ error: 'Премия подается только за текущую неделю' }, 400)
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

// PUT /guilds/:guildId/bonus/:id/approve - принять (admin/owner, только открытая неделя)
bonus.put('/:guildId/bonus/:id/approve', async (c) => {
  const guildId = c.req.param('guildId')
  const id = c.req.param('id')
  const who = await caller(c, c.env)
  if (!who || !sameGuild(who, guildId)) return c.json({ error: 'Forbidden' }, 403)
  if (who.role !== 'owner' && who.role !== 'bot' && who.role !== 'admin') {
    return c.json({ error: 'Forbidden' }, 403)
  }

  const row: any = await c.env.DB.prepare(
    'SELECT * FROM bonus_reports WHERE id = ? AND guild_id = ?'
  ).bind(id, guildId).first()
  if (!row) return c.json({ error: 'Not found' }, 404)
  if (row.status !== 'pending') return c.json({ error: 'Уже обработана' }, 409)
  if (weekLocked(row.week_end)) {
    return c.json({ error: 'Неделя закрыта: после понедельника принимать нельзя' }, 403)
  }

  // Сумма = полный расчет как в боте (контракты + надбавки за ранг)
  const calc = await calcBonus(c.env, guildId, row.recipient_discord_id, row.week_start, row.week_end)
  const amount = calc.total

  await c.env.DB.prepare(
    'UPDATE bonus_reports SET status = ?, amount = ? WHERE id = ?'
  ).bind('approved', amount, id).run()
  const updated = await c.env.DB.prepare('SELECT * FROM bonus_reports WHERE id = ?').bind(id).first()
  return c.json({ ...updated as object, calc })
})

// PUT /guilds/:guildId/bonus/:id/reject - отклонить (admin/owner, только открытая неделя)
bonus.put('/:guildId/bonus/:id/reject', async (c) => {
  const guildId = c.req.param('guildId')
  const id = c.req.param('id')
  const who = await caller(c, c.env)
  if (!who || !sameGuild(who, guildId)) return c.json({ error: 'Forbidden' }, 403)
  if (who.role !== 'owner' && who.role !== 'bot' && who.role !== 'admin') {
    return c.json({ error: 'Forbidden' }, 403)
  }

  const body = await c.req.json<{ reason?: string }>().catch(() => ({}) as any)
  const row: any = await c.env.DB.prepare(
    'SELECT * FROM bonus_reports WHERE id = ? AND guild_id = ?'
  ).bind(id, guildId).first()
  if (!row) return c.json({ error: 'Not found' }, 404)
  if (row.status !== 'pending') return c.json({ error: 'Уже обработана' }, 409)
  if (weekLocked(row.week_end)) {
    return c.json({ error: 'Неделя закрыта: после понедельника решать нельзя' }, 403)
  }

  await c.env.DB.prepare(
    'UPDATE bonus_reports SET status = ?, reason = ? WHERE id = ?'
  ).bind('rejected', body.reason || row.reason, id).run()
  const updated = await c.env.DB.prepare('SELECT * FROM bonus_reports WHERE id = ?').bind(id).first()
  return c.json(updated)
})

// GET /guilds/:guildId/bonus/export?week_start=&week_end=&comment= - txt выгрузка принятых (admin/owner)
bonus.get('/:guildId/bonus/export', async (c) => {
  const guildId = c.req.param('guildId')
  const who = await caller(c, c.env)
  if (!who || !sameGuild(who, guildId)) return c.json({ error: 'Forbidden' }, 403)
  if (who.role !== 'owner' && who.role !== 'bot' && who.role !== 'admin') {
    return c.json({ error: 'Forbidden' }, 403)
  }

  let weekStart = c.req.query('week_start') || ''
  let weekEnd = c.req.query('week_end') || ''
  if (!weekStart || !weekEnd) {
    // По умолчанию - последняя завершенная неделя
    const now = new Date()
    const day = (now.getUTCDay() + 6) % 7
    const mon = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() - day))
    const prevSun = new Date(mon.getTime() - 86400000)
    const prevMon = new Date(prevSun.getTime() - 6 * 86400000)
    weekStart = prevMon.toISOString().slice(0, 10)
    weekEnd = prevSun.toISOString().slice(0, 10)
  }

  const guild = await c.env.DB.prepare(
    'SELECT guild_name FROM guilds WHERE guild_id = ?'
  ).bind(guildId).first<{ guild_name: string }>()

  const rows = await c.env.DB.prepare(
    `SELECT b.*, u.static as user_static FROM bonus_reports b
     LEFT JOIN users u ON u.discord_id = b.recipient_discord_id AND u.guild_id = b.guild_id
     WHERE b.guild_id = ? AND b.status = 'approved'
     AND b.week_start = ? AND b.week_end = ?
     ORDER BY u.static ASC`
  ).bind(guildId, weekStart, weekEnd).all()

  const commentParam = c.req.query('comment') || ''
  const lines: string[] = [
    `Премия семьи ${guild?.guild_name || guildId} за неделю с ${weekStart} по ${weekEnd}`,
    '',
  ]
  for (const r of rows.results as any[]) {
    const comment = commentParam || `премия за неделю с ${weekStart} по ${weekEnd}`
    lines.push(String(r.user_static || r.recipient_discord_id))
    lines.push(String(r.amount ?? 0))
    lines.push(comment)
    lines.push('')
  }

  return new Response('\uFEFF' + lines.join('\n'), {
    headers: {
      'Content-Type': 'text/plain; charset=utf-8',
      'Content-Disposition': `attachment; filename="bonus_${weekStart}_${weekEnd}.txt"`,
    },
  })
})

export const bonusRoutes = bonus

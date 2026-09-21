import { Hono } from 'hono'
import type { Env } from '../index'
import { verifyToken } from './auth'

const contracts = new Hono<{ Bindings: Env }>()

async function caller(c: any, env: Env) {
  const header = c.req.header('Authorization')
  if (!header?.startsWith('Bearer ')) return null
  const token = header.substring(7)
  if (env.SYNC_SECRET && token === env.SYNC_SECRET) return { role: 'bot' as string, guild_id: undefined as string | undefined, discord_id: undefined as string | undefined }
  const payload: any = await verifyToken(token, env.SECRET_KEY)
  if (!payload) return null
  if (payload.user_type === 'owner') return { role: 'owner', guild_id: undefined, discord_id: undefined }
  return { role: (payload.role || 'user') as string, guild_id: payload.guild_id as string | undefined, discord_id: payload.discord_id as string | undefined }
}

// Типы: рекрут шлет только агитации, юзер - все кроме агитаций
const AGITATION_TYPES = ['агитации-маркетплейс', 'агитации-wn']
const ALL_TYPES = ['активация', 'дары-моря', 'металлургия-сдача', 'металлургия-добыча', 'товары', 'ателье', 'тюнинг', 'курьер-еды', ...AGITATION_TYPES]

// GET /guilds/:guildId/contracts/
contracts.get('/:guildId/contracts/', async (c) => {
  const guildId = c.req.param('guildId')
  const who = await caller(c, c.env)
  if (!who) return c.json({ error: 'Forbidden' }, 403)
  const status = c.req.query('status')
  const contractType = c.req.query('contract_type')
  const discordId = c.req.query('discord_id')
  const since = c.req.query('since')
  const limit = Math.min(parseInt(c.req.query('limit') || '200', 10) || 200, 500)

  let query = 'SELECT * FROM contracts WHERE guild_id = ?'
  const params: any[] = [guildId]

  if (who.role !== 'owner' && who.role !== 'bot' && who.role !== 'admin' && who.role !== 'recruiter') {
    // Обычный юзер видит только свои (параметр игнорируется)
    if (!who.discord_id) return c.json({ error: 'Forbidden' }, 403)
    query += ' AND discord_id = ?'
    params.push(who.discord_id)
  } else if (who.role !== 'owner' && who.role !== 'bot' && who.guild_id !== guildId) {
    return c.json({ error: 'Forbidden' }, 403)
  }

  if (status) {
    query += ' AND status = ?'
    params.push(status)
  }

  if (contractType) {
    query += ' AND contract_type = ?'
    params.push(contractType)
  }

  if (discordId) {
    query += ' AND discord_id = ?'
    params.push(discordId)
  }

  if (since) {
    query += ' AND (created_at >= ? OR updated_at >= ?)'
    params.push(since, since)
  }

  query += ' ORDER BY created_at DESC LIMIT ?'
  params.push(limit)

  const result = await c.env.DB.prepare(query).bind(...params).all()
  return c.json(result.results)
})

// POST /guilds/:guildId/contracts/ - подача контракта с сайта (JSON или multipart со скринами).
// Скрины грузятся в Discord-канал (contracts_upload_channel_id, иначе contracts_log_channel_id),
// в базу едут только CDN-ссылки.
contracts.post('/:guildId/contracts/', async (c) => {
  const guildId = c.req.param('guildId')
  const who = await caller(c, c.env)
  if (!who || !who.discord_id) return c.json({ error: 'Forbidden' }, 403)
  if (who.role !== 'owner' && who.guild_id !== guildId) return c.json({ error: 'Forbidden' }, 403)

  const contentType = c.req.header('Content-Type') || ''
  let contractType = ''
  let price: number | undefined
  let nickname: string | undefined
  let details: Record<string, any> = {}
  let files: File[] = []

  if (contentType.includes('multipart/form-data')) {
    const form = await c.req.parseBody()
    try {
      const payload = JSON.parse(String(form['payload'] || '{}'))
      contractType = String(payload.contract_type || '').trim()
      price = payload.price !== undefined ? Number(payload.price) : undefined
      nickname = payload.nickname ? String(payload.nickname) : undefined
      details = payload.details || {}
    } catch {
      return c.json({ error: 'Bad payload' }, 400)
    }
    for (const [k, v] of Object.entries(form)) {
      if (k.startsWith('file_') && v instanceof File) files.push(v)
    }
  } else {
    const body = await c.req.json<{
      contract_type: string; price?: number; nickname?: string; details?: Record<string, any>;
    }>()
    contractType = String(body.contract_type || '').trim()
    price = body.price
    nickname = body.nickname
    details = body.details || {}
  }

  if (!ALL_TYPES.includes(contractType)) {
    return c.json({ error: 'Неизвестный тип контракта' }, 400)
  }
  if (who.role === 'recruiter' && !AGITATION_TYPES.includes(contractType)) {
    return c.json({ error: 'Рекрут отправляет только агитации' }, 403)
  }
  if (who.role === 'user' && AGITATION_TYPES.includes(contractType)) {
    return c.json({ error: 'Этот тип только для рекрутов' }, 403)
  }

  // Участник сервера?
  if (who.role !== 'owner') {
    const member = await c.env.DB.prepare(
      'SELECT 1 FROM users WHERE discord_id = ? AND guild_id = ? UNION SELECT 1 FROM permissions WHERE discord_id = ? AND guild_id = ? LIMIT 1'
    ).bind(who.discord_id, guildId, who.discord_id, guildId).first()
    if (!member) return c.json({ error: 'Отправлять могут только участники сервера' }, 403)
  }

  // Сколько скринов нужно: товары - 2 окна (хватит 1), маркетплейс - 0, остальные - 1+
  const needFiles = contractType === 'агитации-маркетплейс' ? 0 : contractType === 'товары' ? 1 : 1
  const maxFiles = contractType === 'товары' ? 2 : 10
  if (files.length < needFiles) {
    return c.json({ error: 'Прикрепи скриншот' }, 400)
  }
  if (files.length > maxFiles) {
    return c.json({ error: `Максимум файлов: ${maxFiles}` }, 400)
  }
  for (const f of files) {
    if (f.size > 8 * 1024 * 1024) {
      return c.json({ error: `Файл ${f.name} больше 8 МБ` }, 413)
    }
  }

  // Заливка в Discord-канал
  const attachments: string[] = []
  if (files.length > 0) {
    if (!c.env.DISCORD_BOT_TOKEN) {
      return c.json({ error: 'Загрузка скринов не настроена' }, 502)
    }
    const srow = await c.env.DB.prepare(
      "SELECT setting_key, setting_value FROM guild_settings WHERE guild_id = ? AND setting_key IN ('contracts_upload_channel_id', 'contracts_log_channel_id')"
    ).bind(guildId).all()
    const sMap: Record<string, string> = {}
    for (const r of srow.results as Array<{ setting_key: string; setting_value: string }>) {
      sMap[r.setting_key] = r.setting_value
    }
    const channelId = sMap['contracts_upload_channel_id'] || sMap['contracts_log_channel_id']
    if (!channelId) {
      return c.json({ error: 'Не настроен канал загрузки скринов (админ: Уведомления)' }, 400)
    }
    const fd = new FormData()
    const pingRow = await c.env.DB.prepare(
      "SELECT setting_value FROM guild_settings WHERE guild_id = ? AND setting_key = 'contracts_ping_role_ids'"
    ).bind(guildId).first<{ setting_value: string }>()
    const pingIds = (pingRow?.setting_value || '').split(',').map((s) => s.trim()).filter(Boolean)
    const pings = pingIds.map((id) => `<@&${id}>`).join(' ')
    fd.append('content', `${pings ? pings + '\n' : ''}Контракт ${contractType} от <@${who.discord_id}> (сайт)`)
    files.forEach((f, i) => fd.append(`files[${i}]`, f, f.name))
    const up = await fetch(`${c.env.DISCORD_API_ENDPOINT}/channels/${channelId}/messages`, {
      method: 'POST',
      headers: { Authorization: `Bot ${c.env.DISCORD_BOT_TOKEN}` },
      body: fd,
    })
    if (!up.ok) {
      return c.json({ error: 'Не смог загрузить скрины в Discord' }, 502)
    }
    const msg = await up.json<{ id: string; attachments: Array<{ url: string }> }>()
    for (const a of msg.attachments || []) attachments.push(a.url)
    details.upload = { channel_id: channelId, message_id: msg.id }
  }

  const res = await c.env.DB.prepare(
    'INSERT INTO contracts (guild_id, discord_id, contract_type, nickname, price, status, details, screenshot_url) VALUES (?, ?, ?, ?, ?, ?, ?, ?)'
  ).bind(guildId, who.discord_id, contractType, nickname || who.discord_id,
    price ?? 0, 'pending',
    JSON.stringify({ ...details, attachments }),
    attachments[0] || null).run()
  const row = await c.env.DB.prepare('SELECT * FROM contracts WHERE id = ?')
    .bind(res.meta.last_row_id).first()
  return c.json(row)
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
    static?: string;
  }>()

  if (!body.ts || !body.discord_id || !body.contract_type) {
    return c.json({ error: 'Missing ts, discord_id or contract_type' }, 400)
  }

  const st = (body.status || 'PENDING').toUpperCase()
  const status = st === 'APPROVED' ? 'approved' : st === 'REJECTED' ? 'rejected' : 'pending'
  const nick = body.nickname || body.discord_id

  await c.env.DB.prepare(
    `INSERT INTO users (discord_id, guild_id, discord_username, static) VALUES (?, ?, ?, ?)
     ON CONFLICT(discord_id, guild_id) DO UPDATE SET
       discord_username = COALESCE(?, discord_username),
       static = COALESCE(?, static)`
  ).bind(body.discord_id, guildId, body.discord_username || null, body.static || null,
    body.discord_username || null, body.static || null).run()

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
  const who = await caller(c, c.env)
  if (!who) return c.json({ error: 'Forbidden' }, 403)

  const contract: any = await c.env.DB.prepare(
    'SELECT * FROM contracts WHERE guild_id = ? AND id = ?'
  ).bind(guildId, contractId).first()

  if (!contract) {
    return c.json({ error: 'Contract not found' }, 404)
  }

  if (who.role !== 'owner' && who.role !== 'bot' && who.role !== 'admin' && who.role !== 'recruiter') {
    if (contract.discord_id !== who.discord_id) return c.json({ error: 'Forbidden' }, 403)
  } else if (who.role !== 'owner' && who.role !== 'bot' && who.guild_id !== guildId) {
    return c.json({ error: 'Forbidden' }, 403)
  }

  return c.json(contract)
})

// POST /guilds/:guildId/contracts/:contractId/claim - взять (staff, можно перезабрать)
contracts.post('/:guildId/contracts/:contractId/claim', async (c) => {
  const guildId = c.req.param('guildId')
  const contractId = c.req.param('contractId')
  const who = await caller(c, c.env)
  if (!who || !who.discord_id) return c.json({ error: 'Forbidden' }, 403)
  if (who.role !== 'owner' && !['admin', 'recruiter'].includes(who.role)) {
    return c.json({ error: 'Forbidden' }, 403)
  }
  if (who.role !== 'owner' && who.guild_id !== guildId) {
    return c.json({ error: 'Forbidden' }, 403)
  }

  const row: any = await c.env.DB.prepare(
    'SELECT * FROM contracts WHERE id = ? AND guild_id = ?'
  ).bind(contractId, guildId).first()
  if (!row) return c.json({ error: 'Contract not found' }, 404)
  if (row.status !== 'pending') return c.json({ error: 'Контракт уже обработан' }, 409)

  await c.env.DB.prepare(
    'UPDATE contracts SET claimed_by = ?, claimed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE id = ?'
  ).bind(who.discord_id, contractId).run()
  const updated = await c.env.DB.prepare('SELECT * FROM contracts WHERE id = ?')
    .bind(contractId).first()
  return c.json(updated)
})
// PUT /guilds/:guildId/contracts/:contractId (admin/owner: approve/reject, только взятые)
contracts.put('/:guildId/contracts/:contractId', async (c) => {
  const guildId = c.req.param('guildId')
  const contractId = c.req.param('contractId')
  const who = await caller(c, c.env)
  if (!who || (who.role !== 'owner' && who.role !== 'bot')) {
    if (who?.role !== 'admin' || who?.guild_id !== guildId) {
      return c.json({ error: 'Forbidden' }, 403)
    }
  }
  const data = await c.req.json<any>()
  if (data.status) {
    const row: any = await c.env.DB.prepare(
      'SELECT claimed_by FROM contracts WHERE id = ? AND guild_id = ?'
    ).bind(contractId, guildId).first()
    if (!row) return c.json({ error: 'Contract not found' }, 404)
    if (!row.claimed_by) {
      return c.json({ error: 'Сначала возьми контракт' }, 409)
    }
  }

  const updates: string[] = []
  const params: any[] = []

  if (data.status) {
    const st = String(data.status).toLowerCase()
    if (!['pending', 'approved', 'rejected', 'completed'].includes(st)) {
      return c.json({ error: 'Invalid status' }, 400)
    }
    updates.push('status = ?')
    params.push(st)
  }

  if (data.admin_notes !== undefined) {
    updates.push('admin_notes = ?')
    params.push(data.admin_notes)
  }

  if (updates.length === 0) {
    return c.json({ error: 'No fields to update' }, 400)
  }

  updates.push('updated_at = CURRENT_TIMESTAMP')
  params.push(guildId, contractId)

  await c.env.DB.prepare(
    `UPDATE contracts SET ${updates.join(', ')} WHERE guild_id = ? AND id = ?`
  ).bind(...params).run()

  return c.json({ message: 'Contract updated' })
})

// DELETE /guilds/:guildId/contracts/:contractId (admin/owner)
contracts.delete('/:guildId/contracts/:contractId', async (c) => {
  const guildId = c.req.param('guildId')
  const contractId = c.req.param('contractId')
  const who = await caller(c, c.env)
  if (!who || (who.role !== 'owner' && who.role !== 'bot')) {
    if (who?.role !== 'admin' || who?.guild_id !== guildId) {
      return c.json({ error: 'Forbidden' }, 403)
    }
  }

  await c.env.DB.prepare(
    'DELETE FROM contracts WHERE guild_id = ? AND id = ?'
  ).bind(guildId, contractId).run()

  return c.json({ message: 'Contract deleted' })
})

export const contractsRoutes = contracts

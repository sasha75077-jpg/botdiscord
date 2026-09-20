import { Hono } from 'hono'
import type { Env } from '../index'
import { verifyToken } from './auth'

const apps = new Hono<{ Bindings: Env }>()

export interface JwtUser {
  user_type: string
  discord_id?: string
  email?: string
  guild_id?: string
  role?: string
}

async function me(c: any, env: Env): Promise<JwtUser | null> {
  const header = c.req.header('Authorization')
  if (!header?.startsWith('Bearer ')) return null
  const payload: any = await verifyToken(header.substring(7), env.SECRET_KEY)
  if (!payload) return null
  return payload as JwtUser
}

function isBot(c: any, env: Env): boolean {
  const token = (c.req.header('Authorization') || '').substring(7)
  return !!env.SYNC_SECRET && token === env.SYNC_SECRET
}

const RANK = { user: 1, recruiter: 2, admin: 3, owner: 4 } as Record<string, number>

function roleOf(u: JwtUser | null): string {
  if (!u) return ''
  if (u.user_type === 'owner') return 'owner'
  return u.role || 'user'
}

// Обогатить discord_id username/avatar через Discord API (бот-токен)
async function enrich(env: Env, discordId: string | null): Promise<{ id: string | null; username: string | null; avatar: string | null }> {
  if (!discordId) return { id: null, username: null, avatar: null }
  try {
    const resp = await fetch(`${env.DISCORD_API_ENDPOINT}/users/${discordId}`, {
      headers: { Authorization: `Bot ${env.DISCORD_BOT_TOKEN}` },
    })
    if (!resp.ok) throw new Error('discord api')
    const u = await resp.json<{ username: string; discriminator: string; avatar: string | null }>()
    const avatar = u.avatar
      ? `https://cdn.discordapp.com/avatars/${discordId}/${u.avatar}.png?size=128`
      : null
    const username = u.discriminator && u.discriminator !== '0' ? `${u.username}#${u.discriminator}` : u.username
    return { id: discordId, username, avatar }
  } catch {
    return { id: discordId, username: null, avatar: null }
  }
}

async function withPeople(env: Env, row: any) {
  const [applicant, taker] = await Promise.all([
    enrich(env, row.discord_id),
    enrich(env, row.claimed_by),
  ])
  return { ...row, applicant, taker }
}

// GET /guilds/:guildId/applications?status= - очередь (recruiter+ своего сервера, owner)
apps.get('/:guildId/applications', async (c) => {
  const guildId = c.req.param('guildId')
  const u = await me(c, c.env)
  const role = roleOf(u)
  if (!u) return c.json({ error: 'Forbidden' }, 403)

  const status = c.req.query('status')
  let query = 'SELECT * FROM applications WHERE guild_id = ?'
  const params: any[] = [guildId]
  if (RANK[role] < RANK.recruiter) {
    // Обычный юзер видит только свои
    if (!u.discord_id) return c.json({ error: 'Forbidden' }, 403)
    query += ' AND discord_id = ?'
    params.push(u.discord_id)
  } else if (role !== 'owner' && u.guild_id !== guildId) {
    return c.json({ error: 'Forbidden' }, 403)
  }
  if (status) {
    query += ' AND status = ?'
    params.push(status)
  }
  query += ' ORDER BY created_at DESC LIMIT 200'
  const result = await c.env.DB.prepare(query).bind(...params).all()
  const items = await Promise.all(result.results.map((r: any) => withPeople(c.env, r)))
  return c.json({ applications: items })
})

// GET /guilds/:guildId/applications/:id - одна заявка (staff + сам кандидат)
apps.get('/:guildId/applications/:id', async (c) => {
  const guildId = c.req.param('guildId')
  const id = c.req.param('id')
  const u = await me(c, c.env)
  if (!u) return c.json({ error: 'Forbidden' }, 403)

  const row: any = await c.env.DB.prepare(
    'SELECT * FROM applications WHERE id = ? AND guild_id = ?'
  ).bind(id, guildId).first()
  if (!row) return c.json({ error: 'Not found' }, 404)

  const role = roleOf(u)
  const isStaff = RANK[role] >= RANK.recruiter && (role === 'owner' || u.guild_id === guildId)
  const isApplicant = u.discord_id === row.discord_id
  if (!isStaff && !isApplicant) return c.json({ error: 'Forbidden' }, 403)

  return c.json(await withPeople(c.env, row))
})

// Проверка: участник сервера + не член семьи (роль family)
async function checkApplicant(env: Env, guildId: string, discordId: string): Promise<string | null> {
  const member = await env.DB.prepare(
    'SELECT 1 FROM users WHERE discord_id = ? AND guild_id = ? UNION SELECT 1 FROM permissions WHERE discord_id = ? AND guild_id = ? LIMIT 1'
  ).bind(discordId, guildId, discordId, guildId).first()
  if (!member) return 'Подавать заявку могут только участники сервера'

  const famRow = await env.DB.prepare(
    "SELECT setting_value FROM guild_settings WHERE guild_id = ? AND setting_key = 'family_member_role_ids'"
  ).bind(guildId).first<{ setting_value: string }>()
  const famIds = (famRow?.setting_value || '').split(',').map((s) => s.trim()).filter(Boolean)
  if (famIds.length === 0) return null

  try {
    const resp = await fetch(`${env.DISCORD_API_ENDPOINT}/guilds/${guildId}/members/${discordId}`, {
      headers: { Authorization: `Bot ${env.DISCORD_BOT_TOKEN}` },
    })
    if (!resp.ok) return null // не смогли проверить - не блокируем
    const data = await resp.json<{ roles: string[] }>()
    if ((data.roles || []).some((r) => famIds.includes(r))) {
      return 'Ты уже состоишь в семье'
    }
  } catch {
    return null
  }
  return null
}

// POST /guilds/:guildId/applications - подать заявку (участник, не член семьи)
apps.post('/:guildId/applications', async (c) => {
  const guildId = c.req.param('guildId')
  const u = await me(c, c.env)
  if (!u || !u.discord_id) return c.json({ error: 'Forbidden' }, 403)
  if (u.user_type !== 'owner') {
    const block = await checkApplicant(c.env, guildId, u.discord_id)
    if (block) return c.json({ error: block }, 403)
  }

  const body = await c.req.json<{ answers?: Record<string, string> }>()
  const answers = body.answers || {}

  // Обязательные вопросы из настроек (по умолчанию - 4 базовых)
  const srow = await c.env.DB.prepare(
    "SELECT setting_value FROM guild_settings WHERE guild_id = ? AND setting_key = 'application_questions'"
  ).bind(guildId).first<{ setting_value: string }>()
  let questions: Array<{ id: string; label: string; required?: boolean; min?: number }> = [
    { id: 'nickname', label: 'Игровой никнейм', required: true },
    { id: 'age', label: 'Возраст', required: true },
    { id: 'experience', label: 'Опыт в игре', required: true },
    { id: 'reason', label: 'Почему хотите вступить', required: true, min: 20 },
  ]
  if (srow?.setting_value) {
    try {
      const parsed = JSON.parse(srow.setting_value)
      if (Array.isArray(parsed) && parsed.length > 0) questions = parsed
    } catch { /* ignore */ }
  }
  for (const q of questions) {
    const v = (answers[q.id] || '').trim()
    if (q.required && !v) return c.json({ error: `Заполни: ${q.label}` }, 400)
    if (q.min && v.length < q.min) return c.json({ error: `"${q.label}" минимум ${q.min} символов` }, 400)
  }

  // Одна открытая заявка на пользователя
  const open = await c.env.DB.prepare(
    "SELECT id FROM applications WHERE guild_id = ? AND discord_id = ? AND status = 'pending' LIMIT 1"
  ).bind(guildId, u.discord_id).first()
  if (open) return c.json({ error: 'У тебя уже есть открытая заявка' }, 409)

  const externalId = crypto.randomUUID()
  const res = await c.env.DB.prepare(
    'INSERT INTO applications (external_id, guild_id, discord_id, status, answers) VALUES (?, ?, ?, ?, ?)'
  ).bind(externalId, guildId, u.discord_id, 'pending', JSON.stringify(answers)).run()
  const row: any = await c.env.DB.prepare('SELECT * FROM applications WHERE id = ?')
    .bind(res.meta.last_row_id).first()
  return c.json(await withPeople(c.env, row))
})

// POST /guilds/:guildId/applications/:id/claim - взять (recruiter+)
apps.post('/:guildId/applications/:id/claim', async (c) => {
  const guildId = c.req.param('guildId')
  const id = c.req.param('id')
  const u = await me(c, c.env)
  const role = roleOf(u)
  if (!u || !u.discord_id || RANK[role] < RANK.recruiter) return c.json({ error: 'Forbidden' }, 403)
  if (role !== 'owner' && u.guild_id !== guildId) return c.json({ error: 'Forbidden' }, 403)

  const row: any = await c.env.DB.prepare(
    'SELECT * FROM applications WHERE id = ? AND guild_id = ?'
  ).bind(id, guildId).first()
  if (!row) return c.json({ error: 'Not found' }, 404)
  if (row.status !== 'pending') return c.json({ error: 'Заявка уже закрыта' }, 409)

  // Взять можно и чужую (перехват), запрет только на закрытые
  await c.env.DB.prepare(
    'UPDATE applications SET claimed_by = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?'
  ).bind(u.discord_id, id).run()
  const updated: any = await c.env.DB.prepare('SELECT * FROM applications WHERE id = ?').bind(id).first()
  return c.json(await withPeople(c.env, updated))
})

// POST /guilds/:guildId/applications/:id/decide - решить (admin+, recruiter только чтение)
apps.post('/:guildId/applications/:id/decide', async (c) => {
  const guildId = c.req.param('guildId')
  const id = c.req.param('id')
  const u = await me(c, c.env)
  const role = roleOf(u)
  if (!u || RANK[role] < RANK.admin) return c.json({ error: 'Forbidden' }, 403)
  if (role !== 'owner' && u.guild_id !== guildId) return c.json({ error: 'Forbidden' }, 403)

  const body = await c.req.json<{ accepted: boolean; reason?: string }>()
  const row: any = await c.env.DB.prepare(
    'SELECT * FROM applications WHERE id = ? AND guild_id = ?'
  ).bind(id, guildId).first()
  if (!row) return c.json({ error: 'Not found' }, 404)
  if (row.status !== 'pending') return c.json({ error: 'Заявка уже закрыта' }, 409)
  if (!row.claimed_by) {
    return c.json({ error: 'Сначала возьми заявку' }, 409)
  }

  await c.env.DB.prepare(
    'UPDATE applications SET status = ?, decided_by = ?, admin_notes = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?'
  ).bind(body.accepted ? 'approved' : 'rejected', u.discord_id || u.email, body.reason || null, id).run()
  const updated: any = await c.env.DB.prepare('SELECT * FROM applications WHERE id = ?').bind(id).first()
  return c.json(await withPeople(c.env, updated))
})

// GET /guilds/:guildId/applications/:id/messages - переписка (staff + кандидат)
apps.get('/:guildId/applications/:id/messages', async (c) => {
  const guildId = c.req.param('guildId')
  const id = c.req.param('id')
  const u = await me(c, c.env)
  if (!u) return c.json({ error: 'Forbidden' }, 403)

  const row: any = await c.env.DB.prepare(
    'SELECT * FROM applications WHERE id = ? AND guild_id = ?'
  ).bind(id, guildId).first()
  if (!row) return c.json({ error: 'Not found' }, 404)

  const role = roleOf(u)
  const isStaff = RANK[role] >= RANK.recruiter && (role === 'owner' || u.guild_id === guildId)
  if (!isStaff && u.discord_id !== row.discord_id) return c.json({ error: 'Forbidden' }, 403)

  const msgs = await c.env.DB.prepare(
    'SELECT * FROM application_messages WHERE application_id = ? ORDER BY created_at ASC LIMIT 500'
  ).bind(id).all()
  return c.json({ messages: msgs.results })
})

// POST /guilds/:guildId/applications/:id/messages - пишет только взявший (или admin/owner)
apps.post('/:guildId/applications/:id/messages', async (c) => {
  const guildId = c.req.param('guildId')
  const id = c.req.param('id')
  const u = await me(c, c.env)
  if (!u || !u.discord_id) return c.json({ error: 'Forbidden' }, 403)

  const row: any = await c.env.DB.prepare(
    'SELECT * FROM applications WHERE id = ? AND guild_id = ?'
  ).bind(id, guildId).first()
  if (!row) return c.json({ error: 'Not found' }, 404)

  const role = roleOf(u)
  const isTaker = row.claimed_by === u.discord_id
  const isPrivileged = RANK[role] >= RANK.admin && (role === 'owner' || u.guild_id === guildId)
  if (!isTaker && !isPrivileged) {
    return c.json({ error: 'Писать может только взявший заявку' }, 403)
  }

  const body = await c.req.json<{ content: string }>()
  const content = (body.content || '').trim().slice(0, 2000)
  if (!content) return c.json({ error: 'Пустое сообщение' }, 400)

  const res = await c.env.DB.prepare(
    'INSERT INTO application_messages (application_id, author_discord_id, content, from_site, delivered_to_discord) VALUES (?, ?, ?, 1, 0)'
  ).bind(id, u.discord_id, content).run()
  return c.json({ id: res.meta.last_row_id })
})

// GET /guilds/:guildId/applications-updates?since= - для бота (SYNC_SECRET): изменения + исходящие
apps.get('/:guildId/applications-updates', async (c) => {
  if (!isBot(c, c.env)) return c.json({ error: 'Forbidden' }, 403)
  const guildId = c.req.param('guildId')
  const since = c.req.query('since') || '1970-01-01 00:00:00'

  const changed = await c.env.DB.prepare(
    'SELECT * FROM applications WHERE guild_id = ? AND updated_at >= ? ORDER BY updated_at ASC LIMIT 100'
  ).bind(guildId, since).all()

  const outbox = await c.env.DB.prepare(
    `SELECT m.* FROM application_messages m
     JOIN applications a ON a.id = m.application_id
     WHERE a.guild_id = ? AND m.delivered_to_discord = 0 AND m.from_site = 1
     ORDER BY m.created_at ASC LIMIT 100`
  ).bind(guildId).all()

  return c.json({ applications: changed.results, outbox: outbox.results })
})

// POST /guilds/:guildId/applications/:id/delivered - бот отметил доставку (SYNC_SECRET)
apps.post('/:guildId/applications/:id/delivered', async (c) => {
  if (!isBot(c, c.env)) return c.json({ error: 'Forbidden' }, 403)
  const id = c.req.param('id')
  const body = await c.req.json<{ message_ids?: number[]; thread_id?: string; log_message_id?: string }>()
  if (body.message_ids?.length) {
    const placeholders = body.message_ids.map(() => '?').join(',')
    await c.env.DB.prepare(
      `UPDATE application_messages SET delivered_to_discord = 1 WHERE id IN (${placeholders})`
    ).bind(...body.message_ids).run()
  }
  if (body.thread_id || body.log_message_id) {
    await c.env.DB.prepare(
      'UPDATE applications SET thread_id = COALESCE(?, thread_id), log_message_id = COALESCE(?, log_message_id) WHERE id = ?'
    ).bind(body.thread_id || null, body.log_message_id || null, id).run()
  }
  return c.json({ ok: true })
})

export const applicationsRoutes = apps

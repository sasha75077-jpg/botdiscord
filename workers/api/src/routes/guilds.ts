import { Hono } from 'hono'
import type { Env } from '../index'
import { verifyToken } from './auth'

const guilds = new Hono<{ Bindings: Env }>()

// GET /guilds/
guilds.get('/', async (c) => {
  const result = await c.env.DB.prepare(
    'SELECT guild_id, guild_name, is_active, joined_at FROM guilds WHERE is_active = 1'
  ).all()

  return c.json(result.results)
})

// GET /guilds/:guildId
guilds.get('/:guildId', async (c) => {
  const guildId = c.req.param('guildId')

  const guild = await c.env.DB.prepare(
    'SELECT * FROM guilds WHERE guild_id = ?'
  ).bind(guildId).first()

  if (!guild) {
    return c.json({ error: 'Guild not found' }, 404)
  }

  const counts = await c.env.DB.prepare(
    `SELECT
      (SELECT COUNT(*) FROM users WHERE guild_id = ?) as total_users,
      (SELECT COUNT(*) FROM contracts WHERE guild_id = ?) as total_contracts,
      (SELECT COUNT(*) FROM contracts WHERE guild_id = ? AND status = 'pending') as pending_contracts`
  ).bind(guildId, guildId, guildId).first()

  return c.json({ ...guild, ...counts })
})

// GET /guilds/:guildId/settings
guilds.get('/:guildId/settings', async (c) => {
  const guildId = c.req.param('guildId')

  const settings = await c.env.DB.prepare(
    'SELECT * FROM guild_settings WHERE guild_id = ?'
  ).bind(guildId).all()

  const settingsObj: Record<string, string> = {}
  const updatedObj: Record<string, string> = {}
  for (const setting of settings.results) {
    settingsObj[setting.setting_key as string] = setting.setting_value as string
    updatedObj[setting.setting_key as string] = setting.updated_at as string
  }

  return c.json({ settings: settingsObj, updated_at: updatedObj })
})

// PUT /guilds/:guildId/settings
// panel_admin_role_ids меняет только owner; остальные ключи - admin+ своего сервера
guilds.put('/:guildId/settings', async (c) => {
  const header = c.req.header('Authorization')
  if (!header?.startsWith('Bearer ')) {
    return c.json({ error: 'Forbidden' }, 403)
  }
  const token = header.substring(7)
  const isBot = !!c.env.SYNC_SECRET && token === c.env.SYNC_SECRET
  let role: string | null = null
  let tokenGuild: string | undefined
  if (!isBot) {
    const payload: any = await verifyToken(token, c.env.SECRET_KEY)
    if (!payload) {
      return c.json({ error: 'Forbidden' }, 403)
    }
    role = payload.role as string
    tokenGuild = payload.guild_id as string | undefined
  }

  const guildId = c.req.param('guildId')
  const { settings } = await c.req.json<{ settings: Record<string, string> }>()

  if (!settings || typeof settings !== 'object') {
    return c.json({ error: 'Missing settings' }, 400)
  }

  if (!isBot && role !== 'owner' && tokenGuild !== guildId) {
    return c.json({ error: 'Not an admin of this guild' }, 403)
  }
  if (!isBot && role !== 'owner' && role !== 'admin') {
    return c.json({ error: 'Admin access required' }, 403)
  }
  if (!isBot && role !== 'owner' && 'panel_admin_role_ids' in settings) {
    return c.json({ error: 'Only owner can bind admin role' }, 403)
  }

  // Update each setting
  for (const [key, value] of Object.entries(settings)) {
    await c.env.DB.prepare(
      `INSERT INTO guild_settings (guild_id, setting_key, setting_value, updated_at)
       VALUES (?, ?, ?, CURRENT_TIMESTAMP)
       ON CONFLICT(guild_id, setting_key) DO UPDATE SET setting_value = ?, updated_at = CURRENT_TIMESTAMP`
    ).bind(guildId, key, value, value).run()
  }

  return c.json({ message: 'Settings updated' })
})

// GET /guilds/:guildId/modules
guilds.get('/:guildId/modules', async (c) => {
  const guildId = c.req.param('guildId')

  const modules = await c.env.DB.prepare(
    'SELECT * FROM guild_modules WHERE guild_id = ?'
  ).bind(guildId).all()

  return c.json({ modules: modules.results })
})

// PUT /guilds/:guildId/modules/:moduleName
guilds.put('/:guildId/modules/:moduleName', async (c) => {
  const guildId = c.req.param('guildId')
  const moduleName = c.req.param('moduleName')
  const isEnabled = c.req.query('is_enabled') === 'true'

  await c.env.DB.prepare(
    `INSERT INTO guild_modules (guild_id, module_name, is_enabled)
     VALUES (?, ?, ?)
     ON CONFLICT(guild_id, module_name) DO UPDATE SET is_enabled = ?`
  ).bind(guildId, moduleName, isEnabled ? 1 : 0, isEnabled ? 1 : 0).run()

  return c.json({ message: 'Module updated' })
})

// GET /guilds/:guildId/discord-roles - роли сервера из Discord (для выпадающих списков)
guilds.get('/:guildId/discord-roles', async (c) => {
  const header = c.req.header('Authorization')
  if (!header?.startsWith('Bearer ')) {
    return c.json({ error: 'Forbidden' }, 403)
  }
  const token = header.substring(7)
  const isBot = !!c.env.SYNC_SECRET && token === c.env.SYNC_SECRET
  if (!isBot) {
    const payload: any = await verifyToken(token, c.env.SECRET_KEY)
    if (!payload || (payload.role !== 'owner' && payload.role !== 'admin')) {
      return c.json({ error: 'Admin access required' }, 403)
    }
  }

  if (!c.env.DISCORD_BOT_TOKEN) {
    return c.json({ error: 'Discord bot token not configured' }, 502)
  }

  const guildId = c.req.param('guildId')
  const resp = await fetch(`${c.env.DISCORD_API_ENDPOINT}/guilds/${guildId}/roles`, {
    headers: { Authorization: `Bot ${c.env.DISCORD_BOT_TOKEN}` },
  })
  if (!resp.ok) {
    return c.json({ error: 'Failed to fetch Discord roles' }, 502)
  }
  const roles = await resp.json<Array<{ id: string; name: string; color: number; position: number }>>()
  return c.json({
    roles: roles
      .map((r) => ({ id: r.id, name: r.name, color: r.color, position: r.position }))
      .sort((a, b) => b.position - a.position),
  })
})

// GET /guilds/:guildId/discord-channels - текстовые каналы (для выбора логов)
guilds.get('/:guildId/discord-channels', async (c) => {
  const header = c.req.header('Authorization')
  if (!header?.startsWith('Bearer ')) {
    return c.json({ error: 'Forbidden' }, 403)
  }
  const token = header.substring(7)
  const isBot = !!c.env.SYNC_SECRET && token === c.env.SYNC_SECRET
  if (!isBot) {
    const payload: any = await verifyToken(token, c.env.SECRET_KEY)
    if (!payload || (payload.role !== 'owner' && payload.role !== 'admin')) {
      return c.json({ error: 'Admin access required' }, 403)
    }
  }

  if (!c.env.DISCORD_BOT_TOKEN) {
    return c.json({ error: 'Discord bot token not configured' }, 502)
  }

  const guildId = c.req.param('guildId')
  const resp = await fetch(`${c.env.DISCORD_API_ENDPOINT}/guilds/${guildId}/channels`, {
    headers: { Authorization: `Bot ${c.env.DISCORD_BOT_TOKEN}` },
  })
  if (!resp.ok) {
    return c.json({ error: 'Failed to fetch Discord channels' }, 502)
  }
  const channels = await resp.json<Array<{ id: string; name: string; type: number; parent_id?: string }>>()
  return c.json({
    channels: channels
      .filter((ch) => ch.type === 0 || ch.type === 5)
      .map((ch) => ({ id: ch.id, name: ch.name, type: ch.type })),
  })
})

// GET /guilds/:guildId/dashboard - сводка для дешборда юзера
guilds.get('/:guildId/dashboard', async (c) => {
  const header = c.req.header('Authorization')
  if (!header?.startsWith('Bearer ')) {
    return c.json({ error: 'Forbidden' }, 403)
  }
  const payload: any = await verifyToken(header.substring(7), c.env.SECRET_KEY)
  if (!payload) {
    return c.json({ error: 'Forbidden' }, 403)
  }
  const isOwner = payload.user_type === 'owner'

  const guildId = c.req.param('guildId')
  if (!isOwner && payload.guild_id !== guildId) {
    return c.json({ error: 'Forbidden' }, 403)
  }
  if (!isOwner && !payload.discord_id) {
    return c.json({ error: 'Forbidden' }, 403)
  }
  const discordId = (payload.discord_id || '') as string

  // Онлайн/всего участников + имя сервера
  let membersTotal: number | null = null
  let membersOnline: number | null = null
  let guildName: string | null = null
  if (c.env.DISCORD_BOT_TOKEN) {
    try {
      const resp = await fetch(
        `${c.env.DISCORD_API_ENDPOINT}/guilds/${guildId}?with_counts=true`,
        { headers: { Authorization: `Bot ${c.env.DISCORD_BOT_TOKEN}` } }
      )
      if (resp.ok) {
        const g = await resp.json<{
          approximate_member_count?: number; approximate_presence_count?: number; name?: string
        }>()
        membersTotal = g.approximate_member_count ?? null
        membersOnline = g.approximate_presence_count ?? null
        guildName = g.name ?? null
      }
    } catch { /* ignore */ }
  }

  const roles = await c.env.DB.prepare(
    `SELECT role, COUNT(*) as c FROM permissions WHERE guild_id = ? AND role IN ('admin','recruiter') GROUP BY role`
  ).bind(guildId).all()
  let admins = 0
  let recruiters = 0
  for (const r of roles.results as Array<{ role: string; c: number }>) {
    if (r.role === 'admin') admins = r.c
    if (r.role === 'recruiter') recruiters = r.c
  }

  const mine = await c.env.DB.prepare(
    `SELECT status, COUNT(*) as c FROM contracts WHERE guild_id = ? AND discord_id = ? GROUP BY status`
  ).bind(guildId, discordId).all()
  const myContracts = { total: 0, approved: 0, pending: 0, rejected: 0 } as Record<string, number>
  for (const r of mine.results as Array<{ status: string; c: number }>) {
    myContracts.total += r.c
    if (r.status in myContracts) myContracts[r.status] = r.c
  }

  const recent = await c.env.DB.prepare(
    'SELECT id, contract_type, price, status, created_at FROM contracts WHERE guild_id = ? AND discord_id = ? ORDER BY created_at DESC LIMIT 5'
  ).bind(guildId, discordId).all()

  // Ранг по Discord-ролям
  let myRank: string | null = null
  let myRankId: number | null = null
  let rankRows: Array<{ id: number; name: string; role_id: string; sort_order: number }> = []
  try {
    if (c.env.DISCORD_BOT_TOKEN) {
      const mresp = await fetch(
        `${c.env.DISCORD_API_ENDPOINT}/guilds/${guildId}/members/${discordId}`,
        { headers: { Authorization: `Bot ${c.env.DISCORD_BOT_TOKEN}` } }
      )
      if (mresp.ok) {
        const member = await mresp.json<{ roles: string[] }>()
        const ranks = await c.env.DB.prepare(
          'SELECT id, name, role_id, sort_order FROM ranks WHERE guild_id = ?'
        ).bind(guildId).all()
        rankRows = ranks.results as typeof rankRows
        let best: typeof rankRows[0] | null = null
        for (const r of rankRows) {
          if (r.role_id && (member.roles || []).includes(r.role_id)) {
            if (!best || r.sort_order > best.sort_order) best = r
          }
        }
        if (best) {
          myRank = best.name
          myRankId = best.id
        }
      }
    }
  } catch { /* ignore */ }

  // Прогресс до следующего ранга
  let progress: any = null
  try {
    if (myRankId !== null) {
      const sorted = [...rankRows].sort((a, b) => a.sort_order - b.sort_order)
      const idx = sorted.findIndex((r) => r.id === myRankId)
      const next = sorted[idx + 1]
      if (next) {
        const fam = await c.env.DB.prepare(
          `SELECT COUNT(*) as c FROM contracts WHERE guild_id = ? AND discord_id = ?
           AND status = 'approved' AND contract_type NOT IN ('тюнинг', 'курьер-еды')`
        ).bind(guildId, discordId).first<{ c: number }>()
        const per = await c.env.DB.prepare(
          `SELECT COUNT(*) as c FROM contracts WHERE guild_id = ? AND discord_id = ?
           AND status = 'approved' AND contract_type IN ('тюнинг', 'курьер-еды')`
        ).bind(guildId, discordId).first<{ c: number }>()
        const reqMain = await c.env.DB.prepare(
          'SELECT family_contracts FROM rank_requirements_main WHERE rank_from = ? AND rank_to = ?'
        ).bind(myRankId, next.id).first<{ family_contracts: number }>()
        const reqAlt = await c.env.DB.prepare(
          'SELECT family_contracts, tuning_contracts FROM rank_requirements_alt WHERE rank_from = ? AND rank_to = ?'
        ).bind(myRankId, next.id).first<{ family_contracts: number; tuning_contracts: number }>()
        progress = {
          next_rank: next.name,
          family_done: fam?.c || 0,
          family_need: reqMain?.family_contracts ?? null,
          personal_done: per?.c || 0,
          personal_need: reqAlt?.tuning_contracts ?? null,
          alt_family_need: reqAlt?.family_contracts ?? null,
        }
      }
    }
  } catch { /* ignore */ }

  return c.json({
    guild_name: guildName,
    members_total: membersTotal,
    members_online: membersOnline,
    admins,
    recruiters,
    my_contracts: myContracts,
    my_recent: recent.results,
    my_rank: myRank,
    progress,
  })
})

// GET /guilds/:guildId/family - члены семьи (роль FAMQ) со статистикой (admin/owner)
guilds.get('/:guildId/family', async (c) => {
  const header = c.req.header('Authorization')
  if (!header?.startsWith('Bearer ')) {
    return c.json({ error: 'Forbidden' }, 403)
  }
  const token = header.substring(7)
  const isBot = !!c.env.SYNC_SECRET && token === c.env.SYNC_SECRET
  if (!isBot) {
    const payload: any = await verifyToken(token, c.env.SECRET_KEY)
    if (!payload || (payload.role !== 'owner' && payload.role !== 'admin')) {
      return c.json({ error: 'Admin access required' }, 403)
    }
    if (payload.role !== 'owner' && payload.guild_id !== c.req.param('guildId')) {
      return c.json({ error: 'Forbidden' }, 403)
    }
  }

  const guildId = c.req.param('guildId')
  const famRow = await c.env.DB.prepare(
    "SELECT setting_value FROM guild_settings WHERE guild_id = ? AND setting_key = 'family_member_role_ids'"
  ).bind(guildId).first<{ setting_value: string }>()
  const famIds = (famRow?.setting_value || '').split(',').map((s) => s.trim()).filter(Boolean)
  if (famIds.length === 0) {
    return c.json({ error: 'Не настроены семейные роли (страница Роли)' }, 400)
  }
  if (!c.env.DISCORD_BOT_TOKEN) {
    return c.json({ error: 'Discord bot token not configured' }, 502)
  }

  const resp = await fetch(
    `${c.env.DISCORD_API_ENDPOINT}/guilds/${guildId}/members?limit=1000`,
    { headers: { Authorization: `Bot ${c.env.DISCORD_BOT_TOKEN}` } }
  )
  if (!resp.ok) {
    return c.json({ error: 'Failed to fetch Discord members' }, 502)
  }
  const members = await resp.json<Array<{
    user: { id: string; username: string; avatar: string | null };
    roles: string[];
  }>>()
  const family = members.filter((m) => (m.roles || []).some((r) => famIds.includes(r)))

  const perms = await c.env.DB.prepare(
    'SELECT discord_id, role FROM permissions WHERE guild_id = ?'
  ).bind(guildId).all()
  const permMap: Record<string, string> = {}
  for (const p of perms.results as Array<{ discord_id: string; role: string }>) {
    permMap[p.discord_id] = p.role
  }
  const stats = await c.env.DB.prepare(
    'SELECT discord_id, status, COUNT(*) as c FROM contracts WHERE guild_id = ? GROUP BY discord_id, status'
  ).bind(guildId).all()
  const statMap: Record<string, any> = {}
  for (const s of stats.results as Array<{ discord_id: string; status: string; c: number }>) {
    const e = (statMap[s.discord_id] = statMap[s.discord_id] || { total: 0, approved: 0, pending: 0, rejected: 0 })
    e.total += s.c
    if (s.status in e) e[s.status] = s.c
  }

  return c.json({
    members: family.map((m) => ({
      discord_id: m.user.id,
      username: m.user.username,
      avatar: m.user.avatar
        ? `https://cdn.discordapp.com/avatars/${m.user.id}/${m.user.avatar}.png?size=128`
        : null,
      panel_role: permMap[m.user.id] || 'user',
      contracts: statMap[m.user.id] || { total: 0, approved: 0, pending: 0, rejected: 0 },
    })),
  })
})

export const guildsRoutes = guilds

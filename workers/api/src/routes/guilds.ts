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

export const guildsRoutes = guilds

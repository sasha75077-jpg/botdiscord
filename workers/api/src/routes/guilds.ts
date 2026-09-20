import { Hono } from 'hono'
import type { Env } from '../index'

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
  ).all()

  const settingsObj: Record<string, string> = {}
  for (const setting of settings.results) {
    settingsObj[setting.setting_key as string] = setting.setting_value as string
  }

  return c.json({ settings: settingsObj })
})

// PUT /guilds/:guildId/settings
guilds.put('/:guildId/settings', async (c) => {
  const guildId = c.req.param('guildId')
  const { settings } = await c.req.json<{ settings: Record<string, string> }>()

  // Update each setting
  for (const [key, value] of Object.entries(settings)) {
    await c.env.DB.prepare(
      `INSERT INTO guild_settings (guild_id, setting_key, setting_value)
       VALUES (?, ?, ?)
       ON CONFLICT(guild_id, setting_key) DO UPDATE SET setting_value = ?`
    ).bind(guildId, key, value, value).run()
  }

  return c.json({ message: 'Settings updated' })
})

// GET /guilds/:guildId/modules
guilds.get('/:guildId/modules', async (c) => {
  const guildId = c.req.param('guildId')

  const modules = await c.env.DB.prepare(
    'SELECT * FROM guild_modules WHERE guild_id = ?'
  ).all()

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

export const guildsRoutes = guilds

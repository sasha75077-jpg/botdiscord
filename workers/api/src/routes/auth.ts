import { Hono } from 'hono'
import { SignJWT, jwtVerify } from 'jose'
import type { Env } from '../index'

const auth = new Hono<{ Bindings: Env }>()

// JWT helpers
async function createToken(payload: any, secret: string, expiresIn: string) {
  const encoder = new TextEncoder()
  const secretKey = encoder.encode(secret)

  const jwt = await new SignJWT(payload)
    .setProtectedHeader({ alg: 'HS256' })
    .setIssuedAt()
    .setExpirationTime(expiresIn)
    .sign(secretKey)

  return jwt
}

export async function verifyToken(token: string, secret: string) {
  try {
    const encoder = new TextEncoder()
    const secretKey = encoder.encode(secret)
    const { payload } = await jwtVerify(token, secretKey)
    return payload
  } catch {
    return null
  }
}

// Пишущий доступ: JWT пользователя или сервисный ключ бота
export async function requireWriter(c: any, env: Env): Promise<boolean> {
  const header = c.req.header('Authorization')
  if (!header?.startsWith('Bearer ')) return false
  const token = header.substring(7)
  if (env.SYNC_SECRET && token === env.SYNC_SECRET) return true
  const payload = await verifyToken(token, env.SECRET_KEY)
  return !!payload
}

// Hash password (simple SHA-256 for now)
async function hashPassword(password: string): Promise<string> {
  const encoder = new TextEncoder()
  const data = encoder.encode(password)
  const hash = await crypto.subtle.digest('SHA-256', data)
  return Array.from(new Uint8Array(hash))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('')
}

// GET /auth/discord/url
auth.get('/discord/url', async (c) => {
  const guildId = c.req.query('guild_id')
  const state = guildId ? `guild:${guildId}` : 'none'

  const params = new URLSearchParams({
    client_id: c.env.DISCORD_CLIENT_ID,
    redirect_uri: `${c.env.FRONTEND_URL}/auth/callback`, // Discord redirects to frontend
    response_type: 'code',
    scope: 'identify guilds email',
    state,
  })

  const url = `${c.env.DISCORD_API_ENDPOINT}/oauth2/authorize?${params}`
  return c.json({ url })
})

// POST /auth/discord/callback
auth.post('/discord/callback', async (c) => {
  const { code, guild_id } = await c.req.json<{ code: string; guild_id?: string }>()

  if (!code) {
    return c.json({ error: 'Missing code' }, 400)
  }

  try {
    // Exchange code for token
    const tokenResponse = await fetch(`${c.env.DISCORD_API_ENDPOINT}/oauth2/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        client_id: c.env.DISCORD_CLIENT_ID,
        client_secret: c.env.DISCORD_CLIENT_SECRET,
        grant_type: 'authorization_code',
        code,
        redirect_uri: `${c.env.FRONTEND_URL}/auth/callback`,
      }),
    })

    if (!tokenResponse.ok) {
      return c.json({ error: 'Failed to exchange code' }, 400)
    }

    const tokenData = await tokenResponse.json<{ access_token: string }>()

    // Get user info
    const userResponse = await fetch(`${c.env.DISCORD_API_ENDPOINT}/users/@me`, {
      headers: { Authorization: `Bearer ${tokenData.access_token}` },
    })

    if (!userResponse.ok) {
      return c.json({ error: 'Failed to get user info' }, 400)
    }

    const userData = await userResponse.json<{ id: string }>()
    const discordId = userData.id

    // Get user guilds
    const guildsResponse = await fetch(`${c.env.DISCORD_API_ENDPOINT}/users/@me/guilds`, {
      headers: { Authorization: `Bearer ${tokenData.access_token}` },
    })

    if (!guildsResponse.ok) {
      return c.json({ error: 'Failed to get guilds' }, 400)
    }

    const userGuilds = await guildsResponse.json<Array<{ id: string }>>()

    let targetGuildId: string

    if (guild_id) {
      // Check user is in this guild
      const userGuildIds = userGuilds.map(g => g.id)
      if (!userGuildIds.includes(guild_id)) {
        return c.json({ error: 'You are not a member of this guild' }, 403)
      }
      targetGuildId = guild_id
    } else {
      // Find first registered guild
      const registeredGuilds = await c.env.DB.prepare(
        'SELECT guild_id FROM guilds WHERE is_active = 1'
      ).all<{ guild_id: string }>()

      const registeredGuildIds = registeredGuilds.results.map(g => g.guild_id)
      const userGuildIds = userGuilds.map(g => g.id)
      const commonGuilds = userGuildIds.filter(id => registeredGuildIds.includes(id))

      if (commonGuilds.length === 0) {
        return c.json({ error: 'You are not a member of any registered guild' }, 404)
      }

      targetGuildId = commonGuilds[0]
    }

    // Get user role
    const permission = await c.env.DB.prepare(
      'SELECT role FROM permissions WHERE discord_id = ? AND guild_id = ?'
    ).bind(discordId, targetGuildId).first<{ role: string }>()

    const role = permission?.role || 'user'

    // Create JWT tokens
    const accessToken = await createToken(
      {
        user_type: 'discord',
        discord_id: discordId,
        guild_id: targetGuildId,
        role,
      },
      c.env.SECRET_KEY,
      '1h'
    )

    const refreshToken = await createToken(
      {
        user_type: 'discord',
        discord_id: discordId,
        guild_id: targetGuildId,
        role,
      },
      c.env.SECRET_KEY,
      '7d'
    )

    return c.json({
      access_token: accessToken,
      refresh_token: refreshToken,
    })
  } catch (error) {
    console.error('OAuth callback error:', error)
    return c.json({ error: 'Internal server error' }, 500)
  }
})

// POST /auth/owner/login
auth.post('/owner/login', async (c) => {
  const { email, password } = await c.req.json<{ email: string; password: string }>()

  // Get or create owner account
  let owner = await c.env.DB.prepare(
    'SELECT * FROM owner_account WHERE id = 1'
  ).first<{ email: string; password_hash: string }>()

  if (!owner) {
    const passwordHash = await hashPassword(c.env.OWNER_PASSWORD)
    await c.env.DB.prepare(
      'INSERT INTO owner_account (id, email, password_hash) VALUES (1, ?, ?)'
    ).bind(c.env.OWNER_EMAIL, passwordHash).run()

    owner = { email: c.env.OWNER_EMAIL, password_hash: passwordHash }
  }

  // Verify credentials
  if (owner.email !== email) {
    return c.json({ error: 'Incorrect email or password' }, 401)
  }

  const passwordHash = await hashPassword(password)
  if (owner.password_hash !== passwordHash) {
    return c.json({ error: 'Incorrect email or password' }, 401)
  }

  // Update last login
  await c.env.DB.prepare(
    'UPDATE owner_account SET last_login = CURRENT_TIMESTAMP WHERE id = 1'
  ).run()

  // Create tokens
  const accessToken = await createToken(
    { user_type: 'owner', email: owner.email, role: 'owner' },
    c.env.SECRET_KEY,
    '1h'
  )

  const refreshToken = await createToken(
    { user_type: 'owner', email: owner.email, role: 'owner' },
    c.env.SECRET_KEY,
    '7d'
  )

  return c.json({
    access_token: accessToken,
    refresh_token: refreshToken,
  })
})

// POST /auth/refresh
auth.post('/refresh', async (c) => {
  const { refresh_token } = await c.req.json<{ refresh_token: string }>()

  const payload = await verifyToken(refresh_token, c.env.SECRET_KEY)

  if (!payload) {
    return c.json({ error: 'Invalid or expired refresh token' }, 401)
  }

  const userType = payload.user_type as string

  let accessToken: string
  let newRefreshToken: string

  if (userType === 'owner') {
    accessToken = await createToken(
      { user_type: 'owner', email: payload.email, role: 'owner' },
      c.env.SECRET_KEY,
      '1h'
    )
    newRefreshToken = await createToken(
      { user_type: 'owner', email: payload.email, role: 'owner' },
      c.env.SECRET_KEY,
      '7d'
    )
  } else if (userType === 'discord') {
    // Refresh role from DB
    const permission = await c.env.DB.prepare(
      'SELECT role FROM permissions WHERE discord_id = ? AND guild_id = ?'
    ).bind(payload.discord_id as string, payload.guild_id as string)
      .first<{ role: string }>()

    const role = permission?.role || 'user'

    accessToken = await createToken(
      {
        user_type: 'discord',
        discord_id: payload.discord_id,
        guild_id: payload.guild_id,
        role,
      },
      c.env.SECRET_KEY,
      '1h'
    )
    newRefreshToken = await createToken(
      {
        user_type: 'discord',
        discord_id: payload.discord_id,
        guild_id: payload.guild_id,
        role,
      },
      c.env.SECRET_KEY,
      '7d'
    )
  } else {
    return c.json({ error: 'Invalid token payload' }, 400)
  }

  return c.json({
    access_token: accessToken,
    refresh_token: newRefreshToken,
  })
})

// POST /auth/switch - сменить активный сервер (discord-сессии)
auth.post('/switch', async (c) => {
  const authHeader = c.req.header('Authorization')

  if (!authHeader?.startsWith('Bearer ')) {
    return c.json({ error: 'Missing authorization' }, 401)
  }

  const payload = await verifyToken(authHeader.substring(7), c.env.SECRET_KEY)

  if (!payload || payload.user_type !== 'discord') {
    return c.json({ error: 'Invalid token' }, 401)
  }

  const { guild_id } = await c.req.json<{ guild_id: string }>()

  if (!guild_id) {
    return c.json({ error: 'Missing guild_id' }, 400)
  }

  const discordId = payload.discord_id as string

  // Проверка членства: строка в users или permissions (данные от бота)
  const member = await c.env.DB.prepare(
    'SELECT 1 FROM users WHERE discord_id = ? AND guild_id = ? UNION SELECT 1 FROM permissions WHERE discord_id = ? AND guild_id = ? LIMIT 1'
  ).bind(discordId, guild_id, discordId, guild_id).first()

  if (!member) {
    return c.json({ error: 'You are not a member of this guild' }, 403)
  }

  const permission = await c.env.DB.prepare(
    'SELECT role FROM permissions WHERE discord_id = ? AND guild_id = ?'
  ).bind(discordId, guild_id).first<{ role: string }>()

  const role = permission?.role || 'user'

  const accessToken = await createToken(
    { user_type: 'discord', discord_id: discordId, guild_id, role },
    c.env.SECRET_KEY,
    '1h'
  )
  const refreshToken = await createToken(
    { user_type: 'discord', discord_id: discordId, guild_id, role },
    c.env.SECRET_KEY,
    '7d'
  )

  return c.json({ access_token: accessToken, refresh_token: refreshToken })
})

// GET /auth/me
auth.get('/me', async (c) => {
  const authHeader = c.req.header('Authorization')

  if (!authHeader?.startsWith('Bearer ')) {
    return c.json({ error: 'Missing authorization' }, 401)
  }

  const token = authHeader.substring(7)
  const payload = await verifyToken(token, c.env.SECRET_KEY)

  if (!payload) {
    return c.json({ error: 'Invalid token' }, 401)
  }

  return c.json(payload)
})

export const authRoutes = auth

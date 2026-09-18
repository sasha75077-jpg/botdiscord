import { Hono } from 'hono'
import { cors } from 'hono/cors'
import { authRoutes } from './routes/auth'
import { guildsRoutes } from './routes/guilds'
import { contractsRoutes } from './routes/contracts'
import { usersRoutes } from './routes/users'
import { permissionsRoutes } from './routes/permissions'

export interface Env {
  DB: D1Database
  CREDENTIALS_BUCKET?: R2Bucket
  CACHE?: KVNamespace
  DISCORD_CLIENT_ID: string
  DISCORD_CLIENT_SECRET: string
  DISCORD_BOT_TOKEN: string
  SECRET_KEY: string
  OWNER_EMAIL: string
  OWNER_PASSWORD: string
  DISCORD_API_ENDPOINT: string
  FRONTEND_URL: string
}

const app = new Hono<{ Bindings: Env }>()

// CORS
app.use('*', cors({
  origin: ['https://botdiscord-87a.pages.dev', 'http://localhost:5173'],
  credentials: true,
}))

// Health check
app.get('/health', (c) => c.json({ status: 'ok', timestamp: new Date().toISOString() }))

// Routes
app.route('/auth', authRoutes)
app.route('/guilds', guildsRoutes)
app.route('/contracts', contractsRoutes)
app.route('/users', usersRoutes)
app.route('/permissions', permissionsRoutes)

export default app

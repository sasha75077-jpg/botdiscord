import { Hono } from 'hono'
import type { Env } from '../index'
import { verifyToken } from './auth'

const prices = new Hono<{ Bindings: Env }>()

async function isAdmin(c: any, env: Env): Promise<boolean> {
  const header = c.req.header('Authorization')
  if (!header?.startsWith('Bearer ')) return false
  const token = header.substring(7)
  if (env.SYNC_SECRET && token === env.SYNC_SECRET) return true
  const payload: any = await verifyToken(token, env.SECRET_KEY)
  return payload?.role === 'owner' || payload?.role === 'admin'
}

// GET /prices - открытый прайс
prices.get('/', async (c) => {
  const result = await c.env.DB.prepare(
    'SELECT item_key, price, updated_at FROM prices ORDER BY item_key ASC'
  ).all()
  return c.json({ prices: result.results })
})

// PUT /prices - только админ/овнер (и бот): {items: {key: price}}
prices.put('/', async (c) => {
  if (!(await isAdmin(c, c.env))) return c.json({ error: 'Forbidden' }, 403)
  const body = await c.req.json<{ items?: Record<string, number> }>()
  const items = body.items || {}
  const keys = Object.keys(items).filter((k) => k.trim())
  if (keys.length === 0) return c.json({ error: 'Empty items' }, 400)
  if (keys.length > 200) return c.json({ error: 'Too many items' }, 400)

  const batch = keys.map((k) => {
    const price = Number(items[k])
    if (!isFinite(price) || price < 0) throw new Error(`Bad price for ${k}`)
    return c.env.DB.prepare(
      `INSERT INTO prices (item_key, price, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)
       ON CONFLICT(item_key) DO UPDATE SET price = ?, updated_at = CURRENT_TIMESTAMP`
    ).bind(k.trim(), price, price)
  })
  await c.env.DB.batch(batch)
  const result = await c.env.DB.prepare(
    'SELECT item_key, price, updated_at FROM prices ORDER BY item_key ASC'
  ).all()
  return c.json({ prices: result.results })
})

export const pricesRoutes = prices

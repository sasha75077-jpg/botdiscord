import type { Env } from '../index'

export interface DiscordPerson {
  id: string | null
  username: string | null
  avatar: string | null
}

// username/avatar по discord id через Bot-токен
export async function enrichPerson(env: Env, discordId: string | null): Promise<DiscordPerson> {
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

// Добавить person: {...} по указанному полю discord id
export async function enrichMany(env: Env, rows: any[], idField: string): Promise<any[]> {
  return Promise.all(
    rows.map(async (r: any) => ({ ...r, person: await enrichPerson(env, r[idField]) }))
  )
}

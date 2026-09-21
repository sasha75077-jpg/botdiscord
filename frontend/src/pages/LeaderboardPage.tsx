import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { guildsApi } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import { Trophy, Search } from 'lucide-react';

function Bar({ done, need }: { done: number; need: number | null }) {
  if (need === null || need <= 0) return <span className="text-gray-400">—</span>;
  const pct = Math.min(100, Math.round((done / need) * 100));
  return (
    <div>
      <div className="h-2 bg-gray-200 dark:bg-dark-700 rounded-full overflow-hidden">
        <div className="h-full bg-primary-600 rounded-full" style={{ width: `${pct}%` }} />
      </div>
      <p className="text-xs text-gray-500 mt-1">{done} / {need}</p>
    </div>
  );
}

export default function LeaderboardPage() {
  const { user } = useAuthStore();
  const guildId = user?.guild_id || '';
  const [q, setQ] = useState('');

  const { data, isLoading, error } = useQuery({
    queryKey: ['leaderboard', guildId],
    queryFn: async () => (await guildsApi.leaderboard(guildId)).data,
    enabled: !!guildId,
  });

  const members: any[] = data?.members || [];
  const query = q.trim().toLowerCase();
  const shown = members.filter((m: any) =>
    !query || (m.username || '').toLowerCase().includes(query)
  );

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold flex items-center gap-2">
        <Trophy size={28} /> Таблица семьи
      </h1>
      <p className="text-gray-600 dark:text-gray-400">
        Выполненные контракты и прогресс каждого до следующего ранга.
      </p>

      <div className="relative max-w-md">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Найти..."
          className="input w-full pl-9"
        />
      </div>

      {isLoading ? (
        <p className="text-gray-500">Загрузка...</p>
      ) : error ? (
        <div className="card text-center py-10">
          <p className="text-red-600 dark:text-red-400 font-medium">
            {(error as any).response?.data?.error || 'Ошибка загрузки'}
          </p>
        </div>
      ) : shown.length === 0 ? (
        <div className="card text-center py-12 text-gray-500">Пусто.</div>
      ) : (
        <div className="space-y-2">
          {shown.map((m: any, i: number) => (
            <div
              key={m.discord_id}
              className={`card flex items-center gap-4 py-3 ${
                m.discord_id === user?.discord_id ? 'ring-2 ring-primary-500' : ''
              }`}
            >
              <p className="font-bold text-gray-400 w-8 text-center flex-shrink-0">{i + 1}</p>
              {m.avatar ? (
                <img src={m.avatar} alt="" className="w-11 h-11 rounded-full flex-shrink-0" />
              ) : (
                <div className="w-11 h-11 rounded-full bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center font-bold text-primary-600 flex-shrink-0">
                  {(m.username || '?')[0]}
                </div>
              )}
              <div className="flex-1 min-w-0">
                <p className="font-semibold truncate">
                  {m.username}
                  {m.discord_id === user?.discord_id ? ' (ты)' : ''}
                </p>
                <p className="text-xs text-gray-500">
                  {m.rank || 'Без ранга'}
                  {m.next_rank ? ` → ${m.next_rank}` : ' • макс'}
                </p>
              </div>
              <div className="hidden md:block w-40 flex-shrink-0">
                <p className="text-xs text-gray-500 mb-1">Семейные</p>
                <Bar done={m.family_done} need={m.family_need} />
              </div>
              <div className="hidden md:block w-40 flex-shrink-0">
                <p className="text-xs text-gray-500 mb-1">Личные</p>
                <Bar done={m.personal_done} need={m.personal_need} />
              </div>
              <div className="text-center flex-shrink-0 w-16">
                <p className="font-bold text-lg">{m.family_done + m.personal_done}</p>
                <p className="text-xs text-gray-500">всего</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

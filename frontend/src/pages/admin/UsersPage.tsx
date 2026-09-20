import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { guildsApi } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import { Users, Search } from 'lucide-react';

type SortKey = 'total' | 'approved' | 'pending' | 'rejected';

export default function UsersPage() {
  const { user } = useAuthStore();
  const guildId = user?.guild_id || '';
  const [q, setQ] = useState('');
  const [sort, setSort] = useState<SortKey>('total');

  const { data, isLoading, error } = useQuery({
    queryKey: ['family', guildId],
    queryFn: async () => (await guildsApi.family(guildId)).data,
    enabled: !!guildId,
  });

  const members: any[] = data?.members || [];
  const query = q.trim().toLowerCase();
  const shown = members
    .filter((m: any) =>
      !query ||
      (m.username || '').toLowerCase().includes(query) ||
      (m.discord_id || '').includes(query)
    )
    .sort((a: any, b: any) => (b.contracts?.[sort] || 0) - (a.contracts?.[sort] || 0));

  const totals = members.reduce(
    (s: any, m: any) => ({
      members: s.members + 1,
      total: s.total + (m.contracts?.total || 0),
      approved: s.approved + (m.contracts?.approved || 0),
    }),
    { members: 0, total: 0, approved: 0 }
  );

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold flex items-center gap-2">
        <Users size={28} /> Семья
      </h1>
      <p className="text-gray-600 dark:text-gray-400">
        Только holders роли семьи: {totals.members} чел. • контрактов: {totals.total} (принято {totals.approved})
      </p>

      <div className="flex gap-2 flex-wrap items-center">
        <div className="relative flex-1 min-w-[200px] max-w-md">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Имя или Discord ID"
            className="input w-full pl-9"
          />
        </div>
        {(['total', 'approved', 'pending', 'rejected'] as SortKey[]).map((k) => (
          <button
            key={k}
            onClick={() => setSort(k)}
            className={`px-3 py-2 rounded-lg text-sm font-medium ${
              sort === k
                ? 'bg-primary-600 text-white'
                : 'bg-gray-100 dark:bg-dark-700 text-gray-700 dark:text-gray-300'
            }`}
          >
            {k === 'total' ? 'Всего' : k === 'approved' ? 'Принято' : k === 'pending' ? 'Ожидают' : 'Отклонено'}
          </button>
        ))}
      </div>

      {isLoading ? (
        <p className="text-gray-500">Загрузка...</p>
      ) : error ? (
        <div className="card text-center py-10">
          <p className="text-red-600 dark:text-red-400 font-medium">
            {(error as any).response?.data?.error || 'Ошибка загрузки'}
          </p>
          <p className="text-sm text-gray-500 mt-2">Проверь привязку семейной роли на странице Роли.</p>
        </div>
      ) : shown.length === 0 ? (
        <div className="card text-center py-12 text-gray-500">Никого не найдено.</div>
      ) : (
        <div className="space-y-2">
          {shown.map((m: any) => (
            <Link key={m.discord_id} to={`/contracts?user=${m.discord_id}`} className="block">
              <div className="card hover:shadow-lg transition-shadow flex items-center gap-4 py-3">
                {m.avatar ? (
                  <img src={m.avatar} alt="" className="w-11 h-11 rounded-full flex-shrink-0" />
                ) : (
                  <div className="w-11 h-11 rounded-full bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center font-bold text-primary-600 flex-shrink-0">
                    {(m.username || '?')[0]}
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <p className="font-semibold truncate">{m.username || m.discord_id}</p>
                  <p className="text-xs text-gray-500 font-mono truncate">
                    {m.discord_id} • {m.panel_role}
                  </p>
                </div>
                <div className="flex gap-4 text-sm text-center flex-shrink-0">
                  <div>
                    <p className="font-bold">{m.contracts?.total || 0}</p>
                    <p className="text-xs text-gray-500">всего</p>
                  </div>
                  <div>
                    <p className="font-bold text-green-600">{m.contracts?.approved || 0}</p>
                    <p className="text-xs text-gray-500">принято</p>
                  </div>
                  <div>
                    <p className="font-bold text-yellow-600">{m.contracts?.pending || 0}</p>
                    <p className="text-xs text-gray-500">ждут</p>
                  </div>
                  <div>
                    <p className="font-bold text-red-500">{m.contracts?.rejected || 0}</p>
                    <p className="text-xs text-gray-500">откл.</p>
                  </div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

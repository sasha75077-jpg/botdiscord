import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { usersApi, guildsApi } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import { User as UserIcon, CheckCircle, AlertTriangle, TrendingUp, FileText, Award } from 'lucide-react';

function Bar({ done, need }: { done: number; need: number | null }) {
  if (need === null || need <= 0) return null;
  const pct = Math.min(100, Math.round((done / need) * 100));
  return (
    <div className="mt-1">
      <div className="h-2 bg-gray-200 dark:bg-dark-700 rounded-full overflow-hidden">
        <div className="h-full bg-primary-600 rounded-full" style={{ width: `${pct}%` }} />
      </div>
      <p className="text-xs text-gray-500 mt-1">{done} / {need} ({pct}%)</p>
    </div>
  );
}

export default function ProfilePage() {
  const { user } = useAuthStore();
  const guildId = user?.guild_id || '';
  const [myStatic, setMyStatic] = useState('');
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const { data } = useQuery({
    queryKey: ['dashboard', guildId],
    queryFn: async () => (await guildsApi.dashboard(guildId)).data,
    enabled: !!guildId,
  });

  const saveStatic = useMutation({
    mutationFn: () => usersApi.setMyStatic(guildId, myStatic),
    onSuccess: () => setMsg({ ok: true, text: 'Static сохранен' }),
    onError: (e: any) => setMsg({ ok: false, text: e.response?.data?.error || 'Ошибка' }),
  });

  const my = data?.my_contracts || { total: 0, approved: 0, pending: 0, rejected: 0 };
  const progress = data?.progress;

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold flex items-center gap-2">
        <UserIcon size={28} /> Мой профиль
      </h1>

      {msg && (
        <div
          className={`p-3 rounded-lg border flex items-center gap-2 ${
            msg.ok
              ? 'bg-green-50 border-green-300 text-green-800 dark:bg-green-900/20 dark:border-green-800 dark:text-green-200'
              : 'bg-red-50 border-red-300 text-red-800 dark:bg-red-900/20 dark:border-red-800 dark:text-red-200'
          }`}
        >
          {msg.ok ? <CheckCircle size={18} /> : <AlertTriangle size={18} />}
          {msg.text}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card bg-gradient-to-br from-primary-50 to-primary-100 dark:from-primary-900/20 dark:to-primary-800/20 border-primary-200 dark:border-primary-800">
          <p className="text-sm text-gray-600 dark:text-gray-400">Discord ID</p>
          <p className="font-mono font-semibold truncate">{user?.discord_id || user?.email}</p>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-3">Роль на сайте</p>
          <p className="font-semibold">{user?.role}</p>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-3">Ранг в семье</p>
          <p className="text-2xl font-bold text-primary-700 dark:text-primary-300">{data?.my_rank || '—'}</p>
        </div>

        <div className="card">
          <p className="font-semibold flex items-center gap-2 mb-2">
            <FileText size={18} /> Мои контракты
          </p>
          <p className="text-3xl font-bold">{my.total}</p>
          <p className="text-sm text-gray-500 mt-1">
            ✅ {my.approved} • ⏳ {my.pending} • ❌ {my.rejected}
          </p>
        </div>

        <div className="card">
          <p className="font-semibold flex items-center gap-2 mb-2">
            <Award size={18} /> Static для премии
          </p>
          <p className="text-sm text-gray-500 mb-2">Попадет в выгрузку выплат.</p>
          <div className="flex gap-2">
            <input
              value={myStatic}
              onChange={(e) => setMyStatic(e.target.value)}
              placeholder="Например: 4132"
              className="input flex-1"
            />
            <button onClick={() => saveStatic.mutate()} disabled={saveStatic.isPending} className="btn btn-primary text-sm">
              ОК
            </button>
          </div>
        </div>
      </div>

      <div className="card">
        <h2 className="text-xl font-bold mb-1 flex items-center gap-2">
          <TrendingUp size={22} /> Путь к следующему рангу
        </h2>
        {!progress ? (
          <p className="text-gray-500 text-sm mt-2">
            {data?.my_rank ? 'Ты на максимальном ранге 🎉' : 'Ранг не определен — нужна роль ранга в Discord.'}
          </p>
        ) : (
          <div className="mt-2">
            <p className="font-semibold">
              {data?.my_rank} → {progress.next_rank}
            </p>
            <div className="mt-3">
              <p className="text-sm font-medium">Семейные контракты (дары, товары, ателье, сдача)</p>
              <Bar done={progress.family_done} need={progress.family_need} />
            </div>
            <div className="mt-3">
              <p className="text-sm font-medium">Личные (тюнинг, курьер)</p>
              <Bar done={progress.personal_done} need={progress.personal_need} />
            </div>
            <p className="text-xs text-gray-500 mt-3">
              Активация и добыча в повышение не засчитываются.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

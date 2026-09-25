import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { bonusApi, usersApi } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import { Award, Send, Download, CheckCircle, XCircle } from 'lucide-react';
import { Link } from 'react-router-dom';

function weekLocked(weekEnd: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(weekEnd || '')) return false;
  const end = Date.parse(weekEnd + 'T00:00:00Z');
  const nowMsk = Date.now() + 3 * 3600000;
  const today = new Date(nowMsk);
  today.setUTCHours(0, 0, 0, 0);
  return today.getTime() > end;
}

export default function BonusPage() {
  const { user } = useAuthStore();
  const queryClient = useQueryClient();
  const guildId = user?.guild_id || '';
  const isOwner = user?.role === 'owner';
  const isAdmin = isOwner || user?.role === 'admin';
  const isStaff = isAdmin || user?.role === 'recruiter';
  const [filterUser, setFilterUser] = useState('');
  const [msg, setMsg] = useState('');
  const [myStatic, setMyStatic] = useState<string | null>(null);
  const [exportWeek, setExportWeek] = useState({ start: '', end: '' });
  const [exportComment, setExportComment] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['bonus', guildId, isStaff ? filterUser : 'mine'],
    queryFn: async () =>
      (await bonusApi.list(guildId, isStaff && filterUser ? { discord_id: filterUser } : {})).data,
    enabled: !!guildId,
  });

  const submit = useMutation({
    mutationFn: () => bonusApi.submit(guildId),
    onSuccess: () => {
      setMsg('');
      queryClient.invalidateQueries({ queryKey: ['bonus', guildId] });
    },
    onError: (e: any) => setMsg(e.response?.data?.error || 'Ошибка подачи'),
  });
  const decide = useMutation({
    mutationFn: ({ id, accepted }: { id: number; accepted: boolean }) =>
      accepted ? bonusApi.approve(guildId, id) : bonusApi.reject(guildId, id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['bonus', guildId] }),
    onError: (e: any) => setMsg(e.response?.data?.error || 'Ошибка решения'),
  });
  const saveStatic = useMutation({
    mutationFn: () => usersApi.setMyStatic(guildId, myStatic || ''),
    onSuccess: () => setMsg('Static сохранен'),
    onError: (e: any) => setMsg(e.response?.data?.error || 'Ошибка сохранения static'),
  });

  const reports: any[] = Array.isArray(data) ? data : [];

  const weekSum = reports
    .filter((r: any) => r.status === 'approved')
    .reduce((s: number, r: any) => s + Number(r.amount || 0), 0);
  const weekCount = reports.filter((r: any) => r.status === 'approved').length;

  const exportTXT = () => {
    const params = new URLSearchParams();
    if (exportWeek.start) params.set('week_start', exportWeek.start);
    if (exportWeek.end) params.set('week_end', exportWeek.end);
    if (exportComment.trim()) params.set('comment', exportComment.trim());
    const token = localStorage.getItem('access_token');
    fetch(`${import.meta.env.VITE_API_URL}/guilds/${guildId}/bonus/export?${params}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    }).then(async (r) => {
      if (!r.ok) {
        const j = await r.json().catch(() => ({}));
        setMsg(j.error || 'Ошибка выгрузки');
        return;
      }
      const blob = await r.blob();
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `bonus_${exportWeek.start || 'last'}_${exportWeek.end || 'week'}.txt`;
      a.click();
      URL.revokeObjectURL(a.href);
    });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-3xl font-bold flex items-center gap-2">
          <Award size={28} /> {isStaff ? 'Премии' : 'Мои премии'}
        </h1>
        <button
          onClick={() => submit.mutate()}
          disabled={submit.isPending}
          className="btn btn-primary flex items-center gap-2"
        >
          <Send size={18} /> Подать за неделю
        </button>
      </div>

      {msg && <div className="p-3 bg-red-50 border border-red-300 text-red-800 rounded-lg">{msg}</div>}

      <p className="text-sm text-gray-500">
        Премия собирается только за текущую неделю. После понедельника 00:00 МСК неделя закрыта:
        принимать/отклонять нельзя, контракты в выплату не идут. Точную сумму с рангами считает бот при принятии в Discord.
      </p>

      {!isStaff && reports.length > 0 && (
        <div className="card bg-gradient-to-br from-green-50 to-green-100 dark:from-green-900/20 dark:to-green-800/20 border-green-200 dark:border-green-800">
          <p className="text-sm text-green-700 dark:text-green-300 font-medium">Принято премий: {weekCount}</p>
          <p className="text-3xl font-bold text-green-900 dark:text-green-100 mt-1">
            {weekSum.toLocaleString('ru-RU')}
          </p>
          <p className="text-xs text-green-600 dark:text-green-400 mt-1">общая сумма принятых</p>
        </div>
      )}

      <div className="card">
        <label className="block text-sm font-medium mb-2">Мой static для выгрузки</label>
        <div className="flex gap-2">
          <input
            value={myStatic ?? ''}
            onChange={(e) => setMyStatic(e.target.value)}
            placeholder={user?.discord_id || 'static'}
            className="input flex-1"
          />
          <button onClick={() => saveStatic.mutate()} className="btn btn-secondary text-sm">
            Сохранить
          </button>
        </div>
      </div>

      {isAdmin && (
        <div className="card">
          <h2 className="text-xl font-bold mb-3">Выгрузка txt (только принятые)</h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
            <input type="date" value={exportWeek.start} onChange={(e) => setExportWeek({ ...exportWeek, start: e.target.value })} className="input" />
            <input type="date" value={exportWeek.end} onChange={(e) => setExportWeek({ ...exportWeek, end: e.target.value })} className="input" />
            <input value={exportComment} onChange={(e) => setExportComment(e.target.value)} placeholder="Комментарий (необязательно)" className="input" />
            <button onClick={exportTXT} className="btn btn-primary flex items-center gap-2">
              <Download size={18} /> Скачать txt
            </button>
          </div>
          <p className="text-sm text-gray-500 mt-2">Пустые даты = последняя завершенная неделя. Формат: static, сумма, комментарий — в столбец.</p>
        </div>
      )}

      {isStaff && (
        <div className="card">
          <label className="block text-sm font-medium mb-2">Фильтр по пользователю (Discord ID)</label>
          <input
            value={filterUser}
            onChange={(e) => setFilterUser(e.target.value.trim())}
            placeholder="Оставь пустым — все"
            className="input w-full max-w-md"
          />
        </div>
      )}

      {isLoading ? (
        <p className="text-gray-500">Загрузка...</p>
      ) : reports.length === 0 ? (
        <div className="card text-center py-12 text-gray-500">Пока пусто.</div>
      ) : (
        <div className="space-y-3">
          {reports.map((r: any) => {
            let contracts: any[] = [];
            try {
              contracts = JSON.parse(r.contracts_json || '[]');
            } catch { /* ignore */ }
            const locked = weekLocked(r.week_end);
            return (
              <div key={r.id} className="card">
                <div className="flex items-center justify-between flex-wrap gap-2 mb-2">
                  <p className="font-semibold">
                    💰 Премия #{r.id} • {r.person?.username || r.discord_id || r.recipient_discord_id}
                  </p>
                  <span className="px-3 py-1 rounded-full text-xs font-medium bg-gray-100 dark:bg-dark-700">
                    {r.status} • {r.week_start}..{r.week_end} • {r.amount}
                    {locked && r.status === 'pending' ? ' • неделя закрыта' : ''}
                  </span>
                </div>
                {contracts.length > 0 ? (
                  <details className="mt-1 text-sm">
                    <summary className="cursor-pointer text-primary-600 dark:text-primary-400">
                      Какие контракты ({contracts.length})
                    </summary>
                    <ul className="mt-1 space-y-1 text-gray-600 dark:text-gray-400">
                      {contracts.map((c: any, i: number) => (
                        <li key={i}>
                          <Link to={`/contracts/${c.contract_id ?? c.id}`} className="hover:underline">
                            #{c.contract_id ?? c.id}
                          </Link>{' '}
                          • {c.contract_type} • {c.amount ?? c.price ?? 0}
                          {c.note ? ` • ${c.note}` : ''}
                        </li>
                      ))}
                    </ul>
                  </details>
                ) : (
                  <p className="text-sm text-gray-500">Без контрактов.</p>
                )}
                {isAdmin && r.status === 'pending' && (
                  <div className="flex gap-2 mt-3">
                    {locked ? (
                      <p className="text-sm text-gray-500">Неделя закрыта — решать нельзя.</p>
                    ) : (
                      <>
                        <button onClick={() => decide.mutate({ id: r.id, accepted: true })} className="btn btn-primary text-sm flex items-center gap-2">
                          <CheckCircle size={16} /> Принять
                        </button>
                        <button onClick={() => decide.mutate({ id: r.id, accepted: false })} className="btn btn-secondary text-sm flex items-center gap-2">
                          <XCircle size={16} /> Отклонить
                        </button>
                      </>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

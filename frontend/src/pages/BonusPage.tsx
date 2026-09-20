import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { bonusApi } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import { Award, Send, Download } from 'lucide-react';
import { Link } from 'react-router-dom';

function toCSV(rows: any[]): string {
  const head = ['id', 'user', 'week_start', 'week_end', 'amount', 'status', 'contracts'];
  const esc = (v: any) => `"${String(v ?? '').replace(/"/g, '""')}"`;
  const lines = [head.join(';')];
  for (const r of rows) {
    let contracts = '';
    try {
      const arr = JSON.parse(r.contracts_json || '[]');
      contracts = arr.map((c: any) => `${c.contract_id}:${c.contract_type}:${c.amount}`).join('|');
    } catch { /* ignore */ }
    lines.push([
      r.id, r.person?.username || r.discord_id || r.recipient_discord_id,
      r.week_start, r.week_end, r.amount, r.status, contracts,
    ].map(esc).join(';'));
  }
  return '﻿' + lines.join('\n');
}

export default function BonusPage() {
  const { user } = useAuthStore();
  const queryClient = useQueryClient();
  const guildId = user?.guild_id || '';
  const isStaff = user?.role === 'owner' || user?.role === 'admin' || user?.role === 'recruiter';
  const [filterUser, setFilterUser] = useState('');
  const [msg, setMsg] = useState('');

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

  const reports: any[] = Array.isArray(data) ? data : [];

  const exportCSV = () => {
    const blob = new Blob([toCSV(reports)], { type: 'text/csv;charset=utf-8' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `bonus_${guildId}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-3xl font-bold flex items-center gap-2">
          <Award size={28} /> {isStaff ? 'Премии' : 'Мои премии'}
        </h1>
        <div className="flex gap-2">
          <button
            onClick={() => submit.mutate()}
            disabled={submit.isPending}
            className="btn btn-primary flex items-center gap-2"
          >
            <Send size={18} /> Подать за неделю
          </button>
          <button onClick={exportCSV} disabled={reports.length === 0} className="btn btn-secondary flex items-center gap-2 disabled:opacity-40">
            <Download size={18} /> CSV
          </button>
        </div>
      </div>

      {msg && <div className="p-3 bg-red-50 border border-red-300 text-red-800 rounded-lg">{msg}</div>}

      <p className="text-sm text-gray-500">
        Премия подается черновиком за текущую неделю, точную сумму считает бот при принятии в Discord.
      </p>

      {isStaff && (
        <div className="card">
          <label className="block text-sm font-medium mb-2">Фильтр по пользователю (Discord ID)</label>
          <input
            value={filterUser}
            onChange={(e) => setFilterUser(e.target.value.trim())}
            placeholder="Оставь пустым — все"
            className="input w-full max-w-md"
          />
          <p className="text-sm text-gray-500 mt-2">
            Удаление отдельных контрактов — через карточку контракта (кнопка у админа).
          </p>
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
            return (
              <div key={r.id} className="card">
                <div className="flex items-center justify-between flex-wrap gap-2 mb-2">
                  <p className="font-semibold">
                    #{r.id} • {r.person?.username || r.discord_id || r.recipient_discord_id}
                  </p>
                  <span className="px-3 py-1 rounded-full text-xs font-medium bg-gray-100 dark:bg-dark-700">
                    {r.status} • {r.week_start}..{r.week_end} • {r.amount}
                  </span>
                </div>
                {contracts.length > 0 ? (
                  <div className="text-sm text-gray-600 dark:text-gray-400">
                    Контрактов: {contracts.length} (принято:{' '}
                    {contracts.filter((c) => (c.amount || 0) > 0 || c.note?.includes('price')).length})
                    <details className="mt-1">
                      <summary className="cursor-pointer text-primary-600 dark:text-primary-400">
                        Какие контракты
                      </summary>
                      <ul className="mt-1 space-y-1">
                        {contracts.map((c: any, i: number) => (
                          <li key={i}>
                            <Link to={`/contracts/${c.contract_id}`} className="hover:underline">
                              #{c.contract_id}
                            </Link>{' '}
                            • {c.contract_type} • {c.amount}
                            {c.note ? ` • ${c.note}` : ''}
                          </li>
                        ))}
                      </ul>
                    </details>
                  </div>
                ) : (
                  <p className="text-sm text-gray-500">Без контрактов.</p>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

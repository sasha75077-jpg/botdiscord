import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ranksApi, guildsApi } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import { TrendingUp, Plus, Trash2, Save, CheckCircle, AlertTriangle } from 'lucide-react';

export default function RanksPage() {
  const { user } = useAuthStore();
  const queryClient = useQueryClient();
  const { guildId: paramGuildId } = useParams<{ guildId: string }>();
  const guildId = paramGuildId ?? user?.guild_id ?? '';
  const isOwner = user?.role === 'owner';
  const canEdit = isOwner || user?.role === 'admin';
  const [newName, setNewName] = useState('');
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const { data } = useQuery({
    queryKey: ['ranks', guildId],
    queryFn: async () => (await ranksApi.list(guildId)).data,
    enabled: !!guildId,
  });
  const { data: reqData } = useQuery({
    queryKey: ['requirements', guildId],
    queryFn: async () => (await ranksApi.requirements(guildId)).data,
    enabled: !!guildId,
  });
  const { data: rolesData } = useQuery({
    queryKey: ['discord-roles', guildId],
    queryFn: async () => (await guildsApi.discordRoles(guildId)).data,
    enabled: !!guildId && canEdit,
  });

  const ranks: any[] = data?.ranks || [];
  const roles: any[] = rolesData?.roles || [];
  const [reqDraft, setReqDraft] = useState<any | null>(null);
  const reqs = reqDraft ?? reqData ?? { main: [], alt: [] };

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['ranks', guildId] });
    queryClient.invalidateQueries({ queryKey: ['requirements', guildId] });
  };

  const bind = useMutation({
    mutationFn: ({ id, role_id }: { id: number; role_id: string }) =>
      ranksApi.update(guildId, id, { role_id: role_id || null }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['ranks', guildId] }),
    onError: (e: any) => setMsg({ ok: false, text: e.response?.data?.error || 'Ошибка' }),
  });
  const create = useMutation({
    mutationFn: () =>
      ranksApi.create(guildId, { name: newName.trim(), sort_order: (ranks.length ? ranks[ranks.length - 1].sort_order : 0) + 1 }),
    onSuccess: () => {
      setNewName('');
      invalidate();
    },
    onError: (e: any) => setMsg({ ok: false, text: e.response?.data?.error || 'Ошибка' }),
  });
  const remove = useMutation({
    mutationFn: (id: number) => ranksApi.remove(guildId, id),
    onSuccess: invalidate,
    onError: (e: any) => setMsg({ ok: false, text: e.response?.data?.error || 'Ошибка' }),
  });
  const saveReq = useMutation({
    mutationFn: () => ranksApi.saveRequirements(guildId, reqs),
    onSuccess: () => {
      setReqDraft(null);
      setMsg({ ok: true, text: 'Требования сохранены, бот подхватит за ~10 минут' });
      queryClient.invalidateQueries({ queryKey: ['requirements', guildId] });
    },
    onError: (e: any) => setMsg({ ok: false, text: e.response?.data?.error || 'Ошибка' }),
  });

  const setReq = (kind: 'main' | 'alt', from: number, to: number, field: string, val: number) => {
    const list = [...(reqs[kind] || [])];
    const i = list.findIndex((r: any) => r.rank_from === from && r.rank_to === to);
    if (i >= 0) list[i] = { ...list[i], [field]: val };
    else list.push({ rank_from: from, rank_to: to, family_contracts: 0, tuning_contracts: 0, [field]: val });
    setReqDraft({ ...reqs, [kind]: list });
  };
  const getReq = (kind: 'main' | 'alt', from: number, to: number, field: string) =>
    (reqs[kind] || []).find((r: any) => r.rank_from === from && r.rank_to === to)?.[field] ?? '';

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold flex items-center gap-2">
        <TrendingUp size={28} /> Ранги и повышения
      </h1>
      <p className="text-gray-600 dark:text-gray-400">
        Привязка рангов к Discord-ролям. В повышение идут: дары моря, товары, ателье, металлургия-сдача
        (семейные) + тюнинг и курьер еды (личные). Активация и добыча не засчитываются.
      </p>

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

      <div className="card">
        <h2 className="text-xl font-bold mb-3">Лестница рангов</h2>
        <div className="space-y-2">
          {ranks.map((r: any, i: number) => (
            <div key={r.id} className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-dark-700 rounded-lg">
              <span className="font-bold text-gray-400 w-6">{i + 1}</span>
              <p className="font-semibold flex-1">{r.name}</p>
              {canEdit ? (
                <select
                  value={r.role_id || ''}
                  onChange={(e) => bind.mutate({ id: r.id, role_id: e.target.value })}
                  className="input max-w-[220px]"
                >
                  <option value="">— роль не привязана —</option>
                  {roles.map((ro: any) => (
                    <option key={ro.id} value={ro.id}>{ro.name}</option>
                  ))}
                </select>
              ) : (
                <span className="text-sm text-gray-500">{r.role_id ? 'привязан' : 'без роли'}</span>
              )}
              {isOwner && (
                <button onClick={() => { if (confirm(`Удалить ранг ${r.name}?`)) remove.mutate(r.id); }} className="btn btn-secondary px-3" title="Удалить">
                  <Trash2 size={16} />
                </button>
              )}
            </div>
          ))}
          {ranks.length === 0 && <p className="text-gray-500">Рангов нет — создай первый.</p>}
        </div>
        {canEdit && (
          <div className="flex gap-2 mt-3">
            <input value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="Название нового ранга" className="input flex-1" />
            <button onClick={() => create.mutate()} disabled={!newName.trim()} className="btn btn-primary flex items-center gap-2 disabled:opacity-40">
              <Plus size={16} /> Добавить
            </button>
          </div>
        )}
      </div>

      <div className="card">
        <h2 className="text-xl font-bold mb-1">Что нужно для следующего ранга</h2>
        <p className="text-sm text-gray-500 mb-3">Семейные контракты (и личные для альтернативной ветки).</p>
        <div className="space-y-2">
          {ranks.slice(0, -1).map((r: any, i: number) => {
            const next = ranks[i + 1];
            return (
              <div key={r.id} className="flex flex-wrap items-center gap-3 p-3 bg-gray-50 dark:bg-dark-700 rounded-lg text-sm">
                <p className="font-semibold flex-1 min-w-[140px]">{r.name} → {next.name}</p>
                <label className="flex items-center gap-2">
                  Семейные
                  <input
                    type="number" min="0"
                    value={getReq('main', r.id, next.id, 'family_contracts')}
                    disabled={!canEdit}
                    onChange={(e) => setReq('main', r.id, next.id, 'family_contracts', Number(e.target.value) || 0)}
                    className="input w-24"
                  />
                </label>
                <label className="flex items-center gap-2">
                  Личные (alt)
                  <input
                    type="number" min="0"
                    value={getReq('alt', r.id, next.id, 'tuning_contracts')}
                    disabled={!canEdit}
                    onChange={(e) => setReq('alt', r.id, next.id, 'tuning_contracts', Number(e.target.value) || 0)}
                    className="input w-24"
                  />
                </label>
              </div>
            );
          })}
        </div>
        {canEdit && ranks.length > 1 && (
          <button onClick={() => saveReq.mutate()} disabled={saveReq.isPending || reqDraft === null} className="btn btn-primary mt-3 flex items-center gap-2 disabled:opacity-40">
            <Save size={16} /> Сохранить требования
          </button>
        )}
      </div>
    </div>
  );
}

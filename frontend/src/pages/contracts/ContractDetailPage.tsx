import { useState } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { contractsApi } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import { ArrowLeft, CheckCircle, XCircle, Hand, Trash2 } from 'lucide-react';

export default function ContractDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const contractId = Number(id);
  const { user } = useAuthStore();
  const queryClient = useQueryClient();
  const guildId = user?.guild_id || '';
  const isOwner = user?.role === 'owner';
  const isAdmin = isOwner || user?.role === 'admin';
  const isStaff = isAdmin || user?.role === 'recruiter';
  const [notes, setNotes] = useState('');
  const [msg, setMsg] = useState('');

  const { data: ct, isLoading } = useQuery({
    queryKey: ['contract', guildId, contractId],
    queryFn: async () => (await contractsApi.get(guildId, contractId)).data,
    enabled: !!guildId && !!contractId,
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['contract', guildId, contractId] });
    queryClient.invalidateQueries({ queryKey: ['contracts', guildId] });
  };

  const decide = useMutation({
    mutationFn: (status: string) =>
      contractsApi.update(guildId, contractId, { status, admin_notes: notes || undefined }),
    onSuccess: invalidate,
    onError: (e: any) => setMsg(e.response?.data?.error || 'Ошибка'),
  });
  const claim = useMutation({
    mutationFn: () => contractsApi.claim(guildId, contractId),
    onSuccess: invalidate,
    onError: (e: any) => setMsg(e.response?.data?.error || 'Ошибка'),
  });
  const remove = useMutation({
    mutationFn: () => contractsApi.delete(guildId, contractId),
    onSuccess: () => navigate('/contracts'),
    onError: (e: any) => setMsg(e.response?.data?.error || 'Ошибка удаления'),
  });

  if (isLoading) return <p className="text-gray-500">Загрузка...</p>;
  if (!ct) return <p className="text-gray-500">Контракт не найден.</p>;

  let details: Record<string, any> = {};
  try {
    Object.assign(details, JSON.parse(ct.details || '{}'));
  } catch { /* ignore */ }

  return (
    <div className="space-y-6">
      <Link to="/contracts" className="btn btn-secondary inline-flex items-center gap-2">
        <ArrowLeft size={18} /> Все контракты
      </Link>
      {isAdmin && (
        <button
          onClick={() => {
            if (confirm(`Удалить контракт #${ct?.id}?`)) remove.mutate();
          }}
          disabled={remove.isPending || !ct}
          className="btn btn-secondary inline-flex items-center gap-2 text-red-600 dark:text-red-400 disabled:opacity-40"
        >
          <Trash2 size={18} /> Удалить
        </button>
      )}

      {msg && <div className="p-3 bg-red-50 border border-red-300 text-red-800 rounded-lg">{msg}</div>}

      <div className="card">
        <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
          <h1 className="text-2xl font-bold">#{ct.id} • {ct.contract_type}</h1>
          <span className="px-3 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300">
            {ct.status}
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm mb-4">
          <p><span className="text-gray-500">Отправитель:</span> <span className="font-mono">{ct.nickname || ct.discord_id}</span></p>
          <p><span className="text-gray-500">Дата:</span> {ct.created_at}</p>
          {ct.price ? <p><span className="text-gray-500">Сумма:</span> {ct.price}</p> : null}
          {ct.claimed_by ? <p><span className="text-gray-500">Взял:</span> <span className="font-mono">{ct.claimed_by}</span></p> : null}
          {ct.admin_notes ? <p><span className="text-gray-500">Заметка:</span> {ct.admin_notes}</p> : null}
        </div>

        {Object.keys(details).length > 0 && (
          <div className="space-y-2 mb-4">
            {Object.entries(details).map(([k, v]) => (
              <div key={k} className="p-3 bg-gray-50 dark:bg-dark-700 rounded-lg text-sm">
                <span className="text-gray-500">{k}: </span>
                <span>{Array.isArray(v) ? v.join(', ') : String(v)}</span>
              </div>
            ))}
          </div>
        )}

        {isStaff && ct.status === 'pending' && !ct.claimed_by && (
          <div className="mt-4">
            <button onClick={() => claim.mutate()} disabled={claim.isPending} className="btn btn-primary flex items-center gap-2">
              <Hand size={18} /> Взять
            </button>
          </div>
        )}

        {isAdmin && ct.status === 'pending' && ct.claimed_by && (
          <div className="flex flex-wrap gap-2 mt-4">
            <input
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Заметка (необязательно)"
              className="input flex-1 min-w-[200px]"
            />
            <button onClick={() => decide.mutate('approved')} disabled={decide.isPending} className="btn btn-primary flex items-center gap-2">
              <CheckCircle size={18} /> Принять
            </button>
            <button onClick={() => decide.mutate('rejected')} disabled={decide.isPending} className="btn btn-secondary flex items-center gap-2">
              <XCircle size={18} /> Отклонить
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { applicationsApi, guildsApi } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import { ArrowLeft, CheckCircle, XCircle, Hand, Send } from 'lucide-react';
import { DEFAULT_QUESTIONS, type Question } from '@/components/ApplicationForm';

function Person({ p, label }: { p: any; label: string }) {
  if (!p?.id) return null;
  return (
    <div className="flex items-center gap-3">
      {p.avatar ? (
        <img src={p.avatar} alt="" className="w-10 h-10 rounded-full" />
      ) : (
        <div className="w-10 h-10 rounded-full bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center font-bold text-primary-600">
          {(p.username || '?')[0]}
        </div>
      )}
      <div>
        <p className="text-xs text-gray-500">{label}</p>
        <p className="font-semibold">{p.username || p.id}</p>
      </div>
    </div>
  );
}

export default function ApplicationDetailPage() {
  const { id } = useParams<{ id: string }>();
  const appId = Number(id);
  const { user } = useAuthStore();
  const queryClient = useQueryClient();
  const guildId = user?.guild_id || '';
  const isOwner = user?.role === 'owner';
  const isAdmin = isOwner || user?.role === 'admin';
  const isStaff = isAdmin || user?.role === 'recruiter';
  const [text, setText] = useState('');
  const [reason, setReason] = useState('');
  const [msg, setMsg] = useState('');

  const { data: app, isLoading } = useQuery({
    queryKey: ['application', guildId, appId],
    queryFn: async () => (await applicationsApi.get(guildId, appId)).data,
    enabled: !!guildId && !!appId,
  });

  const { data: settings } = useQuery({
    queryKey: ['guild-settings', guildId],
    queryFn: async () => (await guildsApi.getSettings(guildId)).data,
    enabled: !!guildId,
  });

  const { data: chat } = useQuery({
    queryKey: ['app-messages', guildId, appId],
    queryFn: async () => (await applicationsApi.messages(guildId, appId)).data,
    enabled: !!guildId && !!appId,
    refetchInterval: 5000,
  });

  let questions: Question[] = DEFAULT_QUESTIONS;
  try {
    const raw = settings?.settings?.application_questions;
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed) && parsed.length > 0) questions = parsed;
    }
  } catch { /* ignore */ }

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['application', guildId, appId] });
    queryClient.invalidateQueries({ queryKey: ['applications', guildId] });
  };

  const claim = useMutation({
    mutationFn: () => applicationsApi.claim(guildId, appId),
    onSuccess: invalidate,
    onError: (e: any) => setMsg(e.response?.data?.error || 'Ошибка'),
  });
  const decide = useMutation({
    mutationFn: (accepted: boolean) => applicationsApi.decide(guildId, appId, accepted, reason || undefined),
    onSuccess: invalidate,
    onError: (e: any) => setMsg(e.response?.data?.error || 'Ошибка'),
  });
  const send = useMutation({
    mutationFn: () => applicationsApi.postMessage(guildId, appId, text.trim()),
    onSuccess: () => {
      setText('');
      queryClient.invalidateQueries({ queryKey: ['app-messages', guildId, appId] });
    },
    onError: (e: any) => setMsg(e.response?.data?.error || 'Ошибка отправки'),
  });

  if (isLoading) return <p className="text-gray-500">Загрузка...</p>;
  if (!app) return <p className="text-gray-500">Заявка не найдена.</p>;

  const answers: Record<string, string> = {};
  try {
    Object.assign(answers, JSON.parse(app.answers || '{}'));
  } catch { /* ignore */ }

  const canWrite =
    app.claimed_by === user?.discord_id || isAdmin;
  const messages: any[] = chat?.messages || [];

  return (
    <div className="space-y-6">
      <Link to="/applications" className="btn btn-secondary inline-flex items-center gap-2">
        <ArrowLeft size={18} /> Все заявки
      </Link>

      {msg && <div className="p-3 bg-red-50 border border-red-300 text-red-800 rounded-lg">{msg}</div>}

      <div className="card">
        <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
          <h1 className="text-2xl font-bold">Заявка #{app.id}</h1>
          <span className="px-3 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300">
            {app.status}
          </span>
        </div>
        <div className="flex flex-wrap gap-6 mb-4">
          <Person p={app.applicant} label="Кандидат" />
          <Person p={app.taker} label="Взял" />
        </div>
        <div className="space-y-3">
          {questions.map((q) => (
            <div key={q.id} className="p-3 bg-gray-50 dark:bg-dark-700 rounded-lg">
              <p className="text-xs text-gray-500 mb-1">{q.label}</p>
              <p className="whitespace-pre-wrap">{answers[q.id] || '—'}</p>
            </div>
          ))}
        </div>

        {app.status === 'pending' && (
          <div className="flex flex-wrap gap-2 mt-4">
            {isStaff && !app.claimed_by && (
              <button onClick={() => claim.mutate()} disabled={claim.isPending} className="btn btn-primary flex items-center gap-2">
                <Hand size={18} /> Взять
              </button>
            )}
            {isAdmin && (
              <>
                <input
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder="Причина (для отклонения)"
                  className="input flex-1 min-w-[200px]"
                />
                <button onClick={() => decide.mutate(true)} disabled={decide.isPending} className="btn btn-primary flex items-center gap-2">
                  <CheckCircle size={18} /> Принять
                </button>
                <button onClick={() => decide.mutate(false)} disabled={decide.isPending} className="btn btn-secondary flex items-center gap-2">
                  <XCircle size={18} /> Отклонить
                </button>
              </>
            )}
          </div>
        )}
      </div>

      <div className="card">
        <h2 className="text-xl font-bold mb-3">Переписка с кандидатом</h2>
        {!app.claimed_by && (
          <p className="text-sm text-gray-500 mb-3">Чат откроется после того, как заявку кто-то возьмет.</p>
        )}
        <div className="space-y-2 max-h-96 overflow-y-auto mb-3">
          {messages.map((m: any) => {
            const mine = m.author_discord_id === user?.discord_id;
            return (
              <div key={m.id} className={`flex ${mine ? 'justify-end' : 'justify-start'}`}>
                <div
                  className={`max-w-[80%] px-3 py-2 rounded-lg text-sm ${
                    mine ? 'bg-primary-600 text-white' : 'bg-gray-100 dark:bg-dark-700'
                  }`}
                >
                  <p className="whitespace-pre-wrap">{m.content}</p>
                  <p className={`text-[11px] mt-1 ${mine ? 'text-primary-100' : 'text-gray-500'}`}>
                    {m.created_at} {m.from_site ? '' : '• Discord'}
                  </p>
                </div>
              </div>
            );
          })}
          {messages.length === 0 && <p className="text-sm text-gray-500">Пока тихо.</p>}
        </div>
        {canWrite ? (
          <div className="flex gap-2">
            <input
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && text.trim()) send.mutate();
              }}
              placeholder="Сообщение кандидату..."
              className="input flex-1"
            />
            <button onClick={() => send.mutate()} disabled={send.isPending || !text.trim()} className="btn btn-primary flex items-center gap-2">
              <Send size={18} />
            </button>
          </div>
        ) : (
          <p className="text-sm text-gray-500">Писать может только взявший заявку (или админ).</p>
        )}
      </div>
    </div>
  );
}

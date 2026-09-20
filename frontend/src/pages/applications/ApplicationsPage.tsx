import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { applicationsApi, guildsApi } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import { ClipboardList, Plus, Trash2, Save } from 'lucide-react';
import { DEFAULT_QUESTIONS, type Question } from '@/components/ApplicationForm';

const STATUS_TABS = [
  { id: undefined, name: 'Все' },
  { id: 'pending', name: 'Ожидают' },
  { id: 'approved', name: 'Принятые' },
  { id: 'rejected', name: 'Отклоненные' },
];

export default function ApplicationsPage() {
  const { user } = useAuthStore();
  const queryClient = useQueryClient();
  const guildId = user?.guild_id || '';
  const canManage = user?.role === 'owner' || user?.role === 'admin';
  const [tab, setTab] = useState<string | undefined>('pending');

  const { data, isLoading } = useQuery({
    queryKey: ['applications', guildId, tab],
    queryFn: async () => (await applicationsApi.list(guildId, tab)).data,
    enabled: !!guildId,
  });

  const { data: settings } = useQuery({
    queryKey: ['guild-settings', guildId],
    queryFn: async () => (await guildsApi.getSettings(guildId)).data,
    enabled: !!guildId && canManage,
  });

  let questions: Question[] = DEFAULT_QUESTIONS;
  try {
    const raw = settings?.settings?.application_questions;
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed) && parsed.length > 0) questions = parsed;
    }
  } catch { /* ignore */ }
  const [draft, setDraft] = useState<Question[] | null>(null);
  const editing = draft ?? questions;

  const saveQuestions = useMutation({
    mutationFn: async () => {
      await guildsApi.updateSettings(guildId, {
        application_questions: JSON.stringify(editing.filter((q) => q.id && q.label)),
      });
    },
    onSuccess: () => {
      setDraft(null);
      queryClient.invalidateQueries({ queryKey: ['guild-settings', guildId] });
    },
  });

  const apps: any[] = data?.applications || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold flex items-center gap-2">
          <ClipboardList size={28} /> Заявки
        </h1>
        <Link to="/applications/new" className="btn btn-primary flex items-center gap-2">
          <Plus size={18} /> Подать заявку
        </Link>
      </div>

      <div className="flex gap-2">
        {STATUS_TABS.map((t) => (
          <button
            key={t.name}
            onClick={() => setTab(t.id)}
            className={`px-4 py-2 rounded-lg text-sm font-medium ${
              tab === t.id
                ? 'bg-primary-600 text-white'
                : 'bg-gray-100 dark:bg-dark-700 text-gray-700 dark:text-gray-300'
            }`}
          >
            {t.name}
          </button>
        ))}
      </div>

      {isLoading ? (
        <p className="text-gray-500">Загрузка...</p>
      ) : apps.length === 0 ? (
        <div className="card text-center py-12 text-gray-500">Заявок нет.</div>
      ) : (
        <div className="space-y-3">
          {apps.map((a: any) => (
            <Link key={a.id} to={`/applications/${a.id}`} className="block">
              <div className="card hover:shadow-lg transition-shadow flex items-center gap-4">
                {a.applicant?.avatar ? (
                  <img src={a.applicant.avatar} alt="" className="w-12 h-12 rounded-full" />
                ) : (
                  <div className="w-12 h-12 rounded-full bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center font-bold text-primary-600">
                    {(a.applicant?.username || '?')[0]}
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <p className="font-semibold truncate">
                    {a.applicant?.username || a.discord_id}
                  </p>
                  <p className="text-sm text-gray-500 truncate">
                    {a.taker?.username ? `Взял: ${a.taker.username}` : 'Не взята'} • {a.created_at}
                  </p>
                </div>
                <span
                  className={`px-3 py-1 rounded-full text-xs font-medium ${
                    a.status === 'approved'
                      ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300'
                      : a.status === 'rejected'
                        ? 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300'
                        : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300'
                  }`}
                >
                  {a.status === 'approved' ? 'Принята' : a.status === 'rejected' ? 'Отклонена' : 'Ожидает'}
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}

      {canManage && (
        <div className="card">
          <h2 className="text-xl font-bold mb-1">Вопросы заявки</h2>
          <p className="text-sm text-gray-500 mb-3">
            Эти же вопросы бот покажет в Discord. Обязательные проверяются при отправке.
          </p>
          <div className="space-y-2">
            {editing.map((q, i) => (
              <div key={i} className="flex gap-2 items-center">
                <input
                  value={q.label}
                  onChange={(e) => {
                    const d = [...editing];
                    d[i] = { ...d[i], label: e.target.value };
                    setDraft(d);
                  }}
                  placeholder="Текст вопроса"
                  className="input flex-1"
                />
                <input
                  value={q.min || ''}
                  onChange={(e) => {
                    const d = [...editing];
                    const v = parseInt(e.target.value, 10);
                    d[i] = { ...d[i], min: isNaN(v) ? undefined : v };
                    setDraft(d);
                  }}
                  placeholder="мин."
                  type="number"
                  className="input w-20"
                />
                <label className="flex items-center gap-1 text-sm whitespace-nowrap">
                  <input
                    type="checkbox"
                    checked={!!q.required}
                    onChange={(e) => {
                      const d = [...editing];
                      d[i] = { ...d[i], required: e.target.checked };
                      setDraft(d);
                    }}
                    className="w-4 h-4"
                  />
                  Обяз.
                </label>
                <button
                  onClick={() => setDraft(editing.filter((_, j) => j !== i))}
                  className="btn btn-secondary px-3"
                  title="Убрать"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            ))}
          </div>
          <div className="flex gap-2 mt-3">
            <button
              onClick={() =>
                setDraft([...editing, { id: `q${Date.now()}`, label: '', required: false }])
              }
              className="btn btn-secondary flex items-center gap-2 text-sm"
            >
              <Plus size={16} /> Добавить вопрос
            </button>
            <button
              onClick={() => saveQuestions.mutate()}
              disabled={saveQuestions.isPending || draft === null}
              className="btn btn-primary flex items-center gap-2 text-sm disabled:opacity-40"
            >
              <Save size={16} /> Сохранить вопросы
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

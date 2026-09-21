import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { panelsApi, guildsApi } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import { LayoutDashboard, Send, CheckCircle, AlertTriangle, Clock } from 'lucide-react';

export default function PanelsPage() {
  const { user } = useAuthStore();
  const queryClient = useQueryClient();
  const guildId = user?.guild_id || '';
  const [adminChannel, setAdminChannel] = useState('');
  const [profileChannel, setProfileChannel] = useState('');
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const { data: channelsData } = useQuery({
    queryKey: ['discord-channels', guildId],
    queryFn: async () => (await guildsApi.discordChannels(guildId)).data,
    enabled: !!guildId,
  });
  const { data: tasks } = useQuery({
    queryKey: ['panel-tasks', guildId],
    queryFn: async () => (await panelsApi.tasks(guildId)).data,
    enabled: !!guildId,
    refetchInterval: 10000,
  });

  const send = useMutation({
    mutationFn: (panel_type: string) =>
      panelsApi.enqueue({
        guild_id: guildId,
        panel_type,
        channel_id: panel_type === 'admin_hub' ? adminChannel : profileChannel,
      }),
    onSuccess: () => {
      setMsg({ ok: true, text: 'Задача поставлена, бот выполнит за ~минуту' });
      queryClient.invalidateQueries({ queryKey: ['panel-tasks', guildId] });
    },
    onError: (e: any) => setMsg({ ok: false, text: e.response?.data?.error || 'Ошибка' }),
  });

  const channels: any[] = channelsData?.channels || [];
  const items: any[] = tasks?.tasks || [];

  const card = (
    title: string,
    desc: string,
    value: string,
    setValue: (v: string) => void,
    panelType: string
  ) => (
    <div className="card">
      <h2 className="text-xl font-bold mb-1">{title}</h2>
      <p className="text-sm text-gray-500 mb-3">{desc}</p>
      <div className="flex gap-2 flex-wrap">
        <select value={value} onChange={(e) => setValue(e.target.value)} className="input flex-1 min-w-[200px]">
          <option value="">— выбери канал —</option>
          {channels.map((ch: any) => (
            <option key={ch.id} value={ch.id}># {ch.name}</option>
          ))}
        </select>
        <button
          onClick={() => send.mutate(panelType)}
          disabled={send.isPending || !value}
          className="btn btn-primary flex items-center gap-2 disabled:opacity-40"
        >
          <Send size={16} /> Отправить
        </button>
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold flex items-center gap-2">
        <LayoutDashboard size={28} /> Панели Discord
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

      {card(
        '🔧 Админ-панель',
        'Хаб со счетчиками очереди и кнопкой открытия панели. Закрепляется, обновляется сам.',
        adminChannel,
        setAdminChannel,
        'admin_hub'
      )}
      {card(
        '👤 Панель игрока',
        'Синяя панелька с кнопкой «Открыть профиль». Закрепляется, обновляется сам.',
        profileChannel,
        setProfileChannel,
        'profile'
      )}

      <div className="card">
        <h2 className="text-xl font-bold mb-3 flex items-center gap-2">
          <Clock size={20} /> Последние задачи
        </h2>
        <div className="space-y-2">
          {items.map((t: any) => (
            <div key={t.id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-dark-700 rounded-lg text-sm">
              <p>
                #{t.id} • {t.panel_type === 'admin_hub' ? 'Админ-панель' : 'Панель игрока'} •{' '}
                <span className="font-mono">{t.channel_id}</span>
              </p>
              <p className={t.status === 'done' ? 'text-green-600' : t.status === 'error' ? 'text-red-600' : 'text-yellow-600'}>
                {t.status === 'done' ? 'Готово' : t.status === 'error' ? `Ошибка: ${t.result}` : 'Ждет бота...'}
              </p>
            </div>
          ))}
          {items.length === 0 && <p className="text-gray-500 text-sm">Пока пусто.</p>}
        </div>
      </div>
    </div>
  );
}

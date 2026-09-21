import { useEffect, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { guildsApi } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import { Bell, Save, CheckCircle, AlertTriangle } from 'lucide-react';

interface DiscordRole {
  id: string;
  name: string;
  color: number;
  position: number;
}

export default function NotificationsPage() {
  const { user } = useAuthStore();
  const queryClient = useQueryClient();
  const guildId = user?.guild_id || '';
  const [logChannel, setLogChannel] = useState('');
  const [pricesChannel, setPricesChannel] = useState('');
  const [uploadChannel, setUploadChannel] = useState('');
  const [appsChannel, setAppsChannel] = useState('');
  const [bonusChannel, setBonusChannel] = useState('');
  const [promoChannel, setPromoChannel] = useState('');
  const [pingIds, setPingIds] = useState<string[]>([]);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const { data: settings } = useQuery({
    queryKey: ['guild-settings', guildId],
    queryFn: async () => (await guildsApi.getSettings(guildId)).data,
    enabled: !!guildId,
  });
  const { data: channelsData } = useQuery({
    queryKey: ['discord-channels', guildId],
    queryFn: async () => (await guildsApi.discordChannels(guildId)).data,
    enabled: !!guildId,
  });
  const { data: rolesData } = useQuery({
    queryKey: ['discord-roles', guildId],
    queryFn: async () => (await guildsApi.discordRoles(guildId)).data,
    enabled: !!guildId,
  });

  useEffect(() => {
    const s = settings?.settings || {};
    setLogChannel(s.contracts_log_channel_id || '');
    setPricesChannel(s.prices_panel_channel_id || '');
    setUploadChannel(s.contracts_upload_channel_id || '');
    setAppsChannel(s.applications_log_channel_id || '');
    setBonusChannel(s.bonus_log_channel_id || '');
    setPromoChannel(s.promo_log_channel_id || '');
    setPingIds(String(s.contracts_ping_role_ids || '').split(',').map((x: string) => x.trim()).filter(Boolean));
  }, [settings]);

  const save = useMutation({
    mutationFn: () =>
      guildsApi.updateSettings(guildId, {
        contracts_log_channel_id: logChannel,
        prices_panel_channel_id: pricesChannel,
        contracts_upload_channel_id: uploadChannel,
        applications_log_channel_id: appsChannel,
        bonus_log_channel_id: bonusChannel,
        promo_log_channel_id: promoChannel,
        contracts_ping_role_ids: pingIds.join(','),
      }),
    onSuccess: () => {
      setMsg({ ok: true, text: 'Сохранено, бот подхватит за ~10 минут' });
      queryClient.invalidateQueries({ queryKey: ['guild-settings', guildId] });
    },
    onError: (e: any) => setMsg({ ok: false, text: e.response?.data?.error || 'Ошибка' }),
  });

  const channels: any[] = channelsData?.channels || [];
  const roles: DiscordRole[] = rolesData?.roles || [];
  const toggle = (id: string) =>
    setPingIds(pingIds.includes(id) ? pingIds.filter((x) => x !== id) : [...pingIds, id]);

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold flex items-center gap-2">
        <Bell size={28} /> Уведомления
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

      <div className="card">
        <h2 className="text-xl font-bold mb-1">Канал контрактов</h2>
        <p className="text-sm text-gray-500 mb-3">
          Сюда уходят контракты с сайта вместе со скринами — это сообщение и есть лог.
          Сюда же бот пишет смену статусов и напоминания взявшим.
        </p>
        <label className="block text-sm font-medium mb-2">Канал</label>
        <select value={uploadChannel} onChange={(e) => setUploadChannel(e.target.value)} className="input w-full max-w-md">
          <option value="">— не выбран —</option>
          {channels.map((ch: any) => (
            <option key={ch.id} value={ch.id}># {ch.name}</option>
          ))}
        </select>
      </div>

      <div className="card">
        <h2 className="text-xl font-bold mb-1">Панель прайса</h2>
        <p className="text-sm text-gray-500 mb-3">
          Бот закрепит там выплаты и будет обновлять сам. При смене канала старая панель удалится.
        </p>
        <label className="block text-sm font-medium mb-2">Канал</label>
        <select value={pricesChannel} onChange={(e) => setPricesChannel(e.target.value)} className="input w-full max-w-md">
          <option value="">— не выбран —</option>
          {channels.map((ch: any) => (
            <option key={ch.id} value={ch.id}># {ch.name}</option>
          ))}
        </select>
      </div>

      <div className="card">
        <h2 className="text-xl font-bold mb-1">Канал заявок</h2>
        <p className="text-sm text-gray-500 mb-3">
          Сюда бот постит панельки заявок с сайта и из Discord.
        </p>
        <label className="block text-sm font-medium mb-2">Канал</label>
        <select value={appsChannel} onChange={(e) => setAppsChannel(e.target.value)} className="input w-full max-w-md">
          <option value="">— не выбран —</option>
          {channels.map((ch: any) => (
            <option key={ch.id} value={ch.id}># {ch.name}</option>
          ))}
        </select>
      </div>

      <div className="card">
        <h2 className="text-xl font-bold mb-1">Канал премий</h2>
        <p className="text-sm text-gray-500 mb-3">
          Сюда бот постит премии, поданные с сайта, с кнопками принятия.
        </p>
        <label className="block text-sm font-medium mb-2">Канал</label>
        <select value={bonusChannel} onChange={(e) => setBonusChannel(e.target.value)} className="input w-full max-w-md">
          <option value="">— не выбран —</option>
          {channels.map((ch: any) => (
            <option key={ch.id} value={ch.id}># {ch.name}</option>
          ))}
        </select>
      </div>

      <div className="card">
        <h2 className="text-xl font-bold mb-1">Канал повышений</h2>
        <p className="text-sm text-gray-500 mb-3">
          Сюда бот постит отчеты на повышение и лестницу рангов (обновляется сама).
        </p>
        <label className="block text-sm font-medium mb-2">Канал</label>
        <select value={promoChannel} onChange={(e) => setPromoChannel(e.target.value)} className="input w-full max-w-md">
          <option value="">— не выбран —</option>
          {channels.map((ch: any) => (
            <option key={ch.id} value={ch.id}># {ch.name}</option>
          ))}
        </select>
      </div>

      <div className="card">
        <h2 className="text-xl font-bold mb-1">Кого тегать на новые контракты</h2>
        <p className="text-sm text-gray-500 mb-3">Можно несколько ролей.</p>
        <div className="max-h-64 overflow-y-auto border border-gray-200 dark:border-dark-600 rounded-lg divide-y divide-gray-100 dark:divide-dark-700 max-w-md">
          {roles.map((r) => (
            <label key={r.id} className="flex items-center gap-3 px-3 py-2 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-dark-700">
              <input
                type="checkbox"
                checked={pingIds.includes(r.id)}
                onChange={() => toggle(r.id)}
                className="w-4 h-4"
              />
              <span
                className="w-3 h-3 rounded-full flex-shrink-0"
                style={{ backgroundColor: r.color ? `#${r.color.toString(16).padStart(6, '0')}` : '#99aab5' }}
              />
              <span className="flex-1 truncate">{r.name}</span>
            </label>
          ))}
          {roles.length === 0 && <p className="px-3 py-4 text-sm text-gray-500">Нет ролей</p>}
        </div>
      </div>

      <div className="card">
        <h2 className="text-xl font-bold mb-1">Заявки</h2>
        <p className="text-sm text-gray-500">
          О новых заявках бот тегает роли из привязки «Recruiter» (страница Роли).
          Канал — тот же лог-канал заявок в Discord.
        </p>
      </div>

      <button onClick={() => save.mutate()} disabled={save.isPending} className="btn btn-primary flex items-center gap-2">
        <Save size={18} /> {save.isPending ? 'Сохранение...' : 'Сохранить'}
      </button>
    </div>
  );
}

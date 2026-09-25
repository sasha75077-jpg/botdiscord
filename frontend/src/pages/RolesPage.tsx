import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { guildsApi, permissionsApi } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import { Shield, Users, AlertTriangle, CheckCircle } from 'lucide-react';

interface DiscordRole {
  id: string;
  name: string;
  color: number;
  position: number;
}

function RoleChecklist({
  roles,
  selected,
  onToggle,
  disabled,
}: {
  roles: DiscordRole[];
  selected: string[];
  onToggle: (id: string) => void;
  disabled?: boolean;
}) {
  return (
    <div className="max-h-64 overflow-y-auto border border-gray-200 dark:border-dark-600 rounded-lg divide-y divide-gray-100 dark:divide-dark-700">
      {roles.map((r) => (
        <label
          key={r.id}
          className={`flex items-center gap-3 px-3 py-2 text-sm hover:bg-gray-50 dark:hover:bg-dark-700 ${
            disabled ? 'opacity-60' : 'cursor-pointer'
          }`}
        >
          <input
            type="checkbox"
            checked={selected.includes(r.id)}
            disabled={disabled}
            onChange={() => onToggle(r.id)}
            className="w-4 h-4"
          />
          <span
            className="w-3 h-3 rounded-full flex-shrink-0"
            style={{ backgroundColor: r.color ? `#${r.color.toString(16).padStart(6, '0')}` : '#99aab5' }}
          />
          <span className="flex-1 truncate">{r.name}</span>
          <span className="text-xs text-gray-400">{r.id}</span>
        </label>
      ))}
      {roles.length === 0 && (
        <p className="px-3 py-4 text-sm text-gray-500">Нет ролей</p>
      )}
    </div>
  );
}

export default function RolesPage() {
  const { guildId: paramGuildId } = useParams<{ guildId: string }>();
  const { user } = useAuthStore();
  const queryClient = useQueryClient();
  const guildId = paramGuildId ?? user?.guild_id;
  const isOwner = user?.role === 'owner';

  const [adminIds, setAdminIds] = useState<string[]>([]);
  const [recruitIds, setRecruitIds] = useState<string[]>([]);
  const [familyIds, setFamilyIds] = useState<string[]>([]);
  const [firstRankIds, setFirstRankIds] = useState<string[]>([]);
  const [callRole, setCallRole] = useState('');
  const [newDiscordId, setNewDiscordId] = useState('');
  const [newRole, setNewRole] = useState('recruiter');
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const { data: guild } = useQuery({
    queryKey: ['guild', guildId],
    queryFn: async () => (await guildsApi.get(guildId!)).data,
    enabled: !!guildId,
  });
  const { data: discordRoles } = useQuery({
    queryKey: ['discord-roles', guildId],
    queryFn: async () => (await guildsApi.discordRoles(guildId!)).data.roles as DiscordRole[],
    enabled: !!guildId,
  });
  const { data: settings } = useQuery({
    queryKey: ['guild-settings', guildId],
    queryFn: async () => (await guildsApi.getSettings(guildId!)).data,
    enabled: !!guildId,
  });
  const { data: permissions } = useQuery({
    queryKey: ['permissions', guildId],
    queryFn: async () => (await permissionsApi.list(guildId!)).data,
  });
  const { data: logs } = useQuery({
    queryKey: ['bot-logs', guildId],
    queryFn: async () => (await guildsApi.botLogs(guildId!)).data,
    enabled: !!guildId,
  });

  useEffect(() => {
    const s = settings?.settings || {};
    const split = (v: any) => String(v || '').split(',').map((x: string) => x.trim()).filter(Boolean);
    setAdminIds(split(s.panel_admin_role_ids));
    setRecruitIds(split(s.panel_recruiter_role_ids));
    setFamilyIds(split(s.family_member_role_ids));
    setFirstRankIds(split(s.first_rank_role_ids));
    setCallRole(String(s.applications_temp_role_id || ''));
  }, [settings]);

  const toggle = (list: string[], setList: (v: string[]) => void, id: string) =>
    setList(list.includes(id) ? list.filter((x) => x !== id) : [...list, id]);

  const saveBindings = useMutation({
    mutationFn: async () => {
      const payload: Record<string, string> = {};
      if (isOwner) {
        payload.panel_admin_role_ids = adminIds.join(',');
      }
      payload.family_member_role_ids = familyIds.join(',');
      payload.first_rank_role_ids = firstRankIds.join(',');
      payload.applications_temp_role_id = callRole;
      payload.panel_recruiter_role_ids = recruitIds.join(',');
      await guildsApi.updateSettings(guildId!, payload);
    },
    onSuccess: () => {
      setMsg({ ok: true, text: 'Привязки сохранены, бот подхватит за ~10 минут' });
      queryClient.invalidateQueries({ queryKey: ['guild-settings', guildId] });
    },
    onError: (e: any) => setMsg({ ok: false, text: e.response?.data?.error || 'Ошибка сохранения' }),
  });

  const grant = useMutation({
    mutationFn: async () => {
      await permissionsApi.assign(guildId!, newDiscordId.trim(), newRole);
    },
    onSuccess: () => {
      setMsg({ ok: true, text: 'Роль выдана' });
      setNewDiscordId('');
      queryClient.invalidateQueries({ queryKey: ['permissions', guildId] });
    },
    onError: (e: any) => setMsg({ ok: false, text: e.response?.data?.error || 'Ошибка выдачи' }),
  });

  const revoke = useMutation({
    mutationFn: async (discordId: string) => {
      await permissionsApi.remove(guildId!, discordId);
    },
    onSuccess: () => {
      setMsg({ ok: true, text: 'Роль снята' });
      queryClient.invalidateQueries({ queryKey: ['permissions', guildId] });
    },
    onError: (e: any) => setMsg({ ok: false, text: e.response?.data?.error || 'Ошибка снятия' }),
  });

  if (!guildId) {
    return <p className="text-gray-500">Выбери сервер в шапке.</p>;
  }

  const perms: any[] = permissions?.permissions || [];
  const logItems: any[] = logs?.logs || [];
  const grantRoles = isOwner ? ['admin', 'recruiter', 'user'] : ['recruiter', 'user'];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-2">
          <Shield size={28} /> Роли — {guild?.guild_name || guildId}
        </h1>
        <p className="text-gray-600 dark:text-gray-400">
          Привязка Discord-ролей к правам панели. Можно выбирать несколько.
        </p>
      </div>

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

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h2 className="text-xl font-bold mb-1">Admin {isOwner ? '' : '(только овнер)'}</h2>
          <p className="text-sm text-gray-500 mb-3">Участники с этими ролями получают полный доступ.</p>
          <RoleChecklist
            roles={discordRoles || []}
            selected={adminIds}
            onToggle={(id) => toggle(adminIds, setAdminIds, id)}
            disabled={!isOwner}
          />
        </div>
        <div className="card">
          <h2 className="text-xl font-bold mb-1">Recruiter</h2>
          <p className="text-sm text-gray-500 mb-3">Агитации и заявки (чтение).</p>
          <RoleChecklist
            roles={discordRoles || []}
            selected={recruitIds}
            onToggle={(id) => toggle(recruitIds, setRecruitIds, id)}
          />
        </div>
      </div>
      {isOwner || user?.role === 'admin' ? (
        <div className="card">
          <h2 className="text-xl font-bold mb-1">Член семьи (FAMQ)</h2>
          <p className="text-sm text-gray-500 mb-3">
            У кого эти роли — уже в семье, заявку подать не сможет (ни с сайта, ни из Discord).
          </p>
          <RoleChecklist
            roles={discordRoles || []}
            selected={familyIds}
            onToggle={(id) => toggle(familyIds, setFamilyIds, id)}
          />
        </div>
      ) : null}
      {isOwner || user?.role === 'admin' ? (
        <div className="card">
          <h2 className="text-xl font-bold mb-1">Первый ранг (уже в семье)</h2>
          <p className="text-sm text-gray-500 mb-3">
            С этими ролями заявку подать нельзя. Ничего не выдается — просто блок.
          </p>
          <RoleChecklist
            roles={discordRoles || []}
            selected={firstRankIds}
            onToggle={(id) => toggle(firstRankIds, setFirstRankIds, id)}
          />
        </div>
      ) : null}
      {isOwner || user?.role === 'admin' ? (
        <div className="card">
          <h2 className="text-xl font-bold mb-1">Обзвон (роль при взятии)</h2>
          <p className="text-sm text-gray-500 mb-3">
            Выдается кандидату, когда рекрутер берет заявку на рассмотрение. Снимается при решении.
          </p>
          <select
            value={callRole}
            onChange={(e) => setCallRole(e.target.value)}
            className="input w-full max-w-md"
          >
            <option value="">— не выбрана —</option>
            {(discordRoles || []).map((r) => (
              <option key={r.id} value={r.id}>{r.name}</option>
            ))}
          </select>
        </div>
      ) : null}
      <button onClick={() => saveBindings.mutate()} disabled={saveBindings.isPending} className="btn btn-primary">
        {saveBindings.isPending ? 'Сохранение...' : 'Сохранить привязки'}
      </button>

      <div className="card">
        <h2 className="text-xl font-bold mb-3 flex items-center gap-2">
          <Users size={22} /> Выдать роль вручную
        </h2>
        <div className="flex flex-col sm:flex-row gap-3">
          <input
            value={newDiscordId}
            onChange={(e) => setNewDiscordId(e.target.value)}
            placeholder="Discord ID пользователя"
            className="input flex-1"
          />
          <select value={newRole} onChange={(e) => setNewRole(e.target.value)} className="input">
            {grantRoles.map((r) => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
          <button onClick={() => grant.mutate()} disabled={grant.isPending || !newDiscordId.trim()} className="btn btn-primary">
            Выдать
          </button>
        </div>
        {!isOwner && (
          <p className="text-sm text-gray-500 mt-2">Админ может выдавать только recruiter/user.</p>
        )}
      </div>

      <div className="card">
        <h2 className="text-xl font-bold mb-3">Назначенные роли ({perms.length})</h2>
        <div className="space-y-2">
          {perms.map((p: any) => (
            <div key={p.discord_id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-dark-700 rounded-lg">
              <div>
                <p className="font-mono font-semibold">{p.discord_id}</p>
                <p className="text-sm text-gray-500">
                  {p.role} • {p.assigned_by === 'discord-sync' ? 'авто (Discord-роль)' : `выдал: ${p.assigned_by || '—'}`}
                </p>
              </div>
              <button
                onClick={() => revoke.mutate(p.discord_id)}
                disabled={revoke.isPending || (!isOwner && (p.role === 'admin' || p.role === 'owner'))}
                className="btn btn-secondary text-sm disabled:opacity-40"
              >
                Снять
              </button>
            </div>
          ))}
          {perms.length === 0 && <p className="text-gray-500 text-sm">Пока никого.</p>}
        </div>
      </div>

      <div className="card">
        <h2 className="text-xl font-bold mb-3">Журнал ошибок бота</h2>
        <div className="space-y-2 max-h-80 overflow-y-auto">
          {logItems.map((l: any) => (
            <div key={l.id} className="p-3 bg-gray-50 dark:bg-dark-700 rounded-lg text-sm">
              <p>{l.message}</p>
              <p className="text-xs text-gray-500 mt-1">{l.created_at} • {l.source}</p>
            </div>
          ))}
          {logItems.length === 0 && <p className="text-gray-500 text-sm">Ошибок нет.</p>}
        </div>
      </div>
    </div>
  );
}

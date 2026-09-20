import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { showcaseApi, guildsApi } from '@/lib/api';
import { Server, Plus, Trash2, Save, Eye, EyeOff } from 'lucide-react';

export default function ShowcaseManagePage() {
  const queryClient = useQueryClient();
  const [form, setForm] = useState({
    guild_id: '', title: '', description: '', majestic_server: '', invite_url: '',
  });

  const { data } = useQuery({
    queryKey: ['showcase-all'],
    queryFn: async () => (await showcaseApi.list(true)).data,
  });
  const { data: guilds } = useQuery({
    queryKey: ['guilds-list'],
    queryFn: async () => (await guildsApi.list()).data,
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['showcase-all'] });

  const create = useMutation({
    mutationFn: () => showcaseApi.create({ ...form, guild_id: form.guild_id || undefined }),
    onSuccess: () => {
      setForm({ guild_id: '', title: '', description: '', majestic_server: '', invite_url: '' });
      invalidate();
    },
  });
  const toggle = useMutation({
    mutationFn: (s: any) => showcaseApi.update(s.id, { is_active: s.is_active ? 0 : 1 }),
    onSuccess: invalidate,
  });
  const saveEdit = useMutation({
    mutationFn: (s: any) => showcaseApi.update(s.id, {
      title: s.title, invite_url: s.invite_url,
      majestic_server: s.majestic_server, description: s.description,
    }),
    onSuccess: () => {
      setEditingId(null);
      invalidate();
    },
  });
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState({ title: '', invite_url: '', majestic_server: '', description: '' });
  const remove = useMutation({
    mutationFn: (id: number) => showcaseApi.remove(id),
    onSuccess: invalidate,
  });

  const servers: any[] = data?.servers || [];
  const guildList: any[] = Array.isArray(guilds) ? guilds : [];

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold flex items-center gap-2">
        <Server size={28} /> Витрина серверов
      </h1>
      <p className="text-gray-600 dark:text-gray-400">
        Видят незнакомцы без доступа. Онлайн и название Discord подтягиваются сами.
      </p>

      <div className="card">
        <h2 className="text-xl font-bold mb-3 flex items-center gap-2">
          <Plus size={20} /> Добавить сервер
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <select
            value={form.guild_id}
            onChange={(e) => setForm({ ...form, guild_id: e.target.value })}
            className="input"
          >
            <option value="">— Discord-сервер (для онлайна) —</option>
            {guildList.map((g: any) => (
              <option key={g.guild_id} value={g.guild_id}>
                {g.guild_name || g.guild_id}
              </option>
            ))}
          </select>
          <input
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            placeholder="Название семьи *"
            className="input"
          />
          <input
            value={form.majestic_server}
            onChange={(e) => setForm({ ...form, majestic_server: e.target.value })}
            placeholder="Сервер Majestic (например, Majestic RP #7)"
            className="input"
          />
          <input
            value={form.invite_url}
            onChange={(e) => setForm({ ...form, invite_url: e.target.value })}
            placeholder="Ссылка-приглашение Discord *"
            className="input"
          />
          <textarea
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            placeholder="Описание"
            className="input md:col-span-2"
          />
        </div>
        <button
          onClick={() => create.mutate()}
          disabled={create.isPending || !form.title.trim() || !form.invite_url.trim()}
          className="btn btn-primary mt-3 disabled:opacity-40"
        >
          Добавить
        </button>
      </div>

      <div className="space-y-3">
        {servers.map((s: any) => (
          <div key={s.id} className="card">
            {editingId === s.id ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <input value={editForm.title} onChange={(e) => setEditForm({ ...editForm, title: e.target.value })} placeholder="Название" className="input" />
                <input value={editForm.invite_url} onChange={(e) => setEditForm({ ...editForm, invite_url: e.target.value })} placeholder="Ссылка-приглашение" className="input" />
                <input value={editForm.majestic_server} onChange={(e) => setEditForm({ ...editForm, majestic_server: e.target.value })} placeholder="Сервер Majestic" className="input" />
                <input value={editForm.description} onChange={(e) => setEditForm({ ...editForm, description: e.target.value })} placeholder="Описание" className="input" />
                <div className="md:col-span-2 flex gap-2">
                  <button onClick={() => saveEdit.mutate({ ...s, ...editForm })} className="btn btn-primary text-sm">Сохранить</button>
                  <button onClick={() => setEditingId(null)} className="btn btn-secondary text-sm">Отмена</button>
                </div>
              </div>
            ) : (
              <div className="flex items-center gap-4">
                <div className="flex-1 min-w-0">
                  <p className="font-semibold">
                    {s.title} {!s.is_active && <span className="text-xs text-gray-400">(скрыт)</span>}
                  </p>
                  <p className="text-sm text-gray-500 truncate">
                    {[s.guild_name, s.majestic_server, s.member_count != null && `${s.member_count} уч.`]
                      .filter(Boolean)
                      .join(' • ')}
                  </p>
                </div>
                <button
                  onClick={() => {
                    setEditingId(s.id);
                    setEditForm({
                      title: s.title || '', invite_url: s.invite_url || '',
                      majestic_server: s.majestic_server || '', description: s.description || '',
                    });
                  }}
                  className="btn btn-secondary px-3 text-sm"
                >
                  Изменить
                </button>
                <button onClick={() => toggle.mutate(s)} className="btn btn-secondary px-3" title="Показать/скрыть">
                  {s.is_active ? <Eye size={16} /> : <EyeOff size={16} />}
                </button>
                <button onClick={() => remove.mutate(s.id)} className="btn btn-secondary px-3" title="Удалить">
                  <Trash2 size={16} />
                </button>
              </div>
            )}
          </div>
        ))}
        {servers.length === 0 && <p className="text-gray-500">Пусто.</p>}
      </div>

      <div className="card">
        <h2 className="text-xl font-bold mb-2 flex items-center gap-2">
          <Save size={20} /> Черновики
        </h2>
        <p className="text-sm text-gray-500">
          Melancholia FAMQ и Squella уже заведены как скрытые — впиши им ссылку и Majestic, нажми глаз.
        </p>
      </div>
    </div>
  );
}

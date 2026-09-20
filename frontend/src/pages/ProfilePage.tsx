import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { usersApi } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import { User as UserIcon, CheckCircle, AlertTriangle } from 'lucide-react';

export default function ProfilePage() {
  const { user } = useAuthStore();
  const guildId = user?.guild_id || '';
  const [myStatic, setMyStatic] = useState('');
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const saveStatic = useMutation({
    mutationFn: () => usersApi.setMyStatic(guildId, myStatic),
    onSuccess: () => setMsg({ ok: true, text: 'Static сохранен' }),
    onError: (e: any) => setMsg({ ok: false, text: e.response?.data?.error || 'Ошибка' }),
  });

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold flex items-center gap-2">
        <UserIcon size={28} /> Мой профиль
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
        <p className="text-sm text-gray-500">Discord ID</p>
        <p className="font-mono font-semibold">{user?.discord_id || user?.email}</p>
        <p className="text-sm text-gray-500 mt-3">Роль</p>
        <p className="font-semibold">{user?.role}</p>
      </div>

      <div className="card">
        <h2 className="text-xl font-bold mb-1">Static для премии</h2>
        <p className="text-sm text-gray-500 mb-3">
          Укажи свой static — он попадет в выгрузку премий для выплат.
        </p>
        <div className="flex gap-2">
          <input
            value={myStatic}
            onChange={(e) => setMyStatic(e.target.value)}
            placeholder="Например: 4132"
            className="input flex-1"
          />
          <button onClick={() => saveStatic.mutate()} disabled={saveStatic.isPending} className="btn btn-primary text-sm">
            Сохранить
          </button>
        </div>
      </div>
    </div>
  );
}

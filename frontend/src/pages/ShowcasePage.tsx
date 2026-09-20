import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { showcaseApi } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import { Server, Users, ExternalLink, LogOut } from 'lucide-react';

export default function ShowcasePage() {
  const { logout } = useAuthStore();
  const { data, isLoading } = useQuery({
    queryKey: ['showcase'],
    queryFn: async () => (await showcaseApi.list()).data,
  });

  const servers: any[] = data?.servers || [];

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-500 to-primary-700 dark:from-dark-900 dark:to-dark-800 px-4 py-10">
      <div className="max-w-3xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">Melancholia</h1>
          <p className="text-primary-100">
            Ты пока не состоишь ни в одном нашем Discord-сервере — доступ к панели закрыт.
            Вступай в семью и заходи снова!
          </p>
        </div>

        {isLoading ? (
          <p className="text-center text-primary-100">Загрузка...</p>
        ) : servers.length === 0 ? (
          <div className="card text-center py-10 text-gray-500">
            Овнер пока не добавил серверы. Загляни позже.
          </div>
        ) : (
          <div className="space-y-4">
            {servers.map((s: any) => (
              <div key={s.id} className="card">
                <div className="flex items-center gap-4">
                  <div className="w-14 h-14 rounded-full bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center flex-shrink-0">
                    <Server className="text-primary-600 dark:text-primary-400" size={26} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h2 className="text-xl font-bold truncate">{s.title}</h2>
                    {s.guild_name && (
                      <p className="text-sm text-gray-500">Discord: {s.guild_name}</p>
                    )}
                    {s.majestic_server && (
                      <p className="text-sm text-gray-500">Majestic: {s.majestic_server}</p>
                    )}
                    {s.description && (
                      <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">{s.description}</p>
                    )}
                    {s.member_count != null && (
                      <p className="text-sm text-gray-500 mt-1 flex items-center gap-1">
                        <Users size={14} /> {s.member_count} участников
                      </p>
                    )}
                  </div>
                  {s.invite_url ? (
                    <a
                      href={s.invite_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn btn-primary flex items-center gap-2 flex-shrink-0"
                    >
                      Вступить <ExternalLink size={16} />
                    </a>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="text-center mt-8 flex items-center justify-center gap-4">
          <Link to="/login" className="text-primary-100 hover:underline text-sm">
            Войти другим аккаунтом
          </Link>
          <button
            onClick={logout}
            className="text-primary-100 hover:underline text-sm flex items-center gap-1"
          >
            <LogOut size={14} /> Выйти
          </button>
        </div>
      </div>
    </div>
  );
}

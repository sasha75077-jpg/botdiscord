import { useQuery } from '@tanstack/react-query';
import { guildsApi } from '@/lib/api';
import { Server, Users, FileText, Clock } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function OwnerDashboard() {
  const { data: guilds, isLoading } = useQuery({
    queryKey: ['guilds'],
    queryFn: async () => {
      const { data } = await guildsApi.list();
      return data;
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
          <p className="mt-4 text-gray-600 dark:text-gray-400">Загрузка...</p>
        </div>
      </div>
    );
  }

  const totalGuilds = guilds?.length || 0;
  const totalUsers = guilds?.reduce((sum: number, g: any) => sum + g.total_users, 0) || 0;
  const totalContracts = guilds?.reduce((sum: number, g: any) => sum + g.total_contracts, 0) || 0;
  const pendingContracts = guilds?.reduce((sum: number, g: any) => sum + g.pending_contracts, 0) || 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold mb-2">🤖 Melancholia Bot Dashboard</h1>
        <p className="text-gray-600 dark:text-gray-400">
          Управление всеми серверами
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Серверов</p>
              <p className="text-3xl font-bold mt-1">{totalGuilds}</p>
            </div>
            <div className="w-12 h-12 bg-primary-100 dark:bg-primary-900/30 rounded-lg flex items-center justify-center">
              <Server className="text-primary-600 dark:text-primary-400" size={24} />
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Пользователей</p>
              <p className="text-3xl font-bold mt-1">{totalUsers}</p>
            </div>
            <div className="w-12 h-12 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
              <Users className="text-blue-600 dark:text-blue-400" size={24} />
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Контрактов</p>
              <p className="text-3xl font-bold mt-1">{totalContracts}</p>
            </div>
            <div className="w-12 h-12 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center">
              <FileText className="text-green-600 dark:text-green-400" size={24} />
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">В ожидании</p>
              <p className="text-3xl font-bold mt-1">{pendingContracts}</p>
            </div>
            <div className="w-12 h-12 bg-yellow-100 dark:bg-yellow-900/30 rounded-lg flex items-center justify-center">
              <Clock className="text-yellow-600 dark:text-yellow-400" size={24} />
            </div>
          </div>
        </div>
      </div>

      {/* Guilds List */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold">Серверы</h2>
          <Link
            to="/owner/settings"
            className="text-sm text-primary-600 dark:text-primary-400 hover:underline"
          >
            Глобальные настройки
          </Link>
        </div>

        {guilds?.length === 0 ? (
          <div className="text-center py-12">
            <Server className="mx-auto h-12 w-12 text-gray-400" />
            <p className="mt-4 text-gray-600 dark:text-gray-400">
              Нет подключенных серверов
            </p>
            <p className="mt-2 text-sm text-gray-500 dark:text-gray-500">
              Добавьте бота на Discord сервер чтобы начать
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {guilds?.map((guild: any) => (
              <Link
                key={guild.guild_id}
                to={`/guilds/${guild.guild_id}`}
                className="block"
              >
                <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-dark-700 rounded-lg hover:bg-gray-100 dark:hover:bg-dark-600 transition-colors cursor-pointer">
                  <div className="flex items-center gap-3">
                    {guild.icon_url ? (
                      <img
                        src={guild.icon_url}
                        alt={guild.guild_name}
                        className="w-12 h-12 rounded-full"
                      />
                    ) : (
                      <div className="w-12 h-12 rounded-full bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center">
                        <Server className="text-primary-600 dark:text-primary-400" size={20} />
                      </div>
                    )}
                    <div>
                      <h3 className="font-semibold text-lg">{guild.guild_name}</h3>
                      <p className="text-sm text-gray-600 dark:text-gray-400">
                        ID: {guild.guild_id}
                      </p>
                    </div>
                  </div>
                  <div className="flex gap-6 text-sm">
                    <div className="text-center">
                      <p className="font-semibold text-lg">{guild.total_users}</p>
                      <p className="text-gray-600 dark:text-gray-400">Польз.</p>
                    </div>
                    <div className="text-center">
                      <p className="font-semibold text-lg">{guild.total_contracts}</p>
                      <p className="text-gray-600 dark:text-gray-400">Контр.</p>
                    </div>
                    <div className="text-center">
                      <p className="font-semibold text-lg text-yellow-600 dark:text-yellow-400">
                        {guild.pending_contracts}
                      </p>
                      <p className="text-gray-600 dark:text-gray-400">Ожид.</p>
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

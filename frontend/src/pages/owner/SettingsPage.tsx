import { useQuery } from '@tanstack/react-query';
import { guildsApi } from '@/lib/api';
import {
  Settings,
  Activity,
  Database,
  Clock,
  Server,
  Users,
  FileText,
  AlertTriangle,
  CheckCircle,
  TrendingUp,
  HardDrive,
} from 'lucide-react';
import { Link } from 'react-router-dom';

export default function OwnerSettingsPage() {
  // Получить все серверы для статистики
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
  const totalUsers = guilds?.reduce((sum: number, g: any) => sum + (g.total_users || 0), 0) || 0;
  const totalContracts = guilds?.reduce((sum: number, g: any) => sum + (g.total_contracts || 0), 0) || 0;
  const pendingContracts = guilds?.reduce((sum: number, g: any) => sum + (g.pending_contracts || 0), 0) || 0;

  const activeGuilds = guilds?.filter((g: any) => g.is_active).length || 0;
  const inactiveGuilds = totalGuilds - activeGuilds;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 bg-gradient-to-br from-purple-500 to-pink-500 rounded-xl flex items-center justify-center shadow-lg">
            <Settings className="text-white" size={32} />
          </div>
          <div>
            <h1 className="text-3xl font-bold">👑 Owner Panel</h1>
            <p className="text-gray-600 dark:text-gray-400">
              Глобальные настройки и управление ботом
            </p>
          </div>
        </div>
        <Link
          to="/"
          className="btn btn-secondary"
        >
          Назад к серверам
        </Link>
      </div>

      {/* Global Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="card bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900/20 dark:to-blue-800/20 border-blue-200 dark:border-blue-800">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-blue-700 dark:text-blue-300 font-medium">Серверов</p>
              <p className="text-3xl font-bold text-blue-900 dark:text-blue-100 mt-1">
                {totalGuilds}
              </p>
              <p className="text-xs text-blue-600 dark:text-blue-400 mt-1">
                {activeGuilds} активных
              </p>
            </div>
            <div className="w-12 h-12 bg-blue-200 dark:bg-blue-900/50 rounded-lg flex items-center justify-center">
              <Server className="text-blue-700 dark:text-blue-300" size={24} />
            </div>
          </div>
        </div>

        <div className="card bg-gradient-to-br from-green-50 to-green-100 dark:from-green-900/20 dark:to-green-800/20 border-green-200 dark:border-green-800">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-green-700 dark:text-green-300 font-medium">Пользователей</p>
              <p className="text-3xl font-bold text-green-900 dark:text-green-100 mt-1">
                {totalUsers}
              </p>
              <p className="text-xs text-green-600 dark:text-green-400 mt-1">
                всего в системе
              </p>
            </div>
            <div className="w-12 h-12 bg-green-200 dark:bg-green-900/50 rounded-lg flex items-center justify-center">
              <Users className="text-green-700 dark:text-green-300" size={24} />
            </div>
          </div>
        </div>

        <div className="card bg-gradient-to-br from-purple-50 to-purple-100 dark:from-purple-900/20 dark:to-purple-800/20 border-purple-200 dark:border-purple-800">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-purple-700 dark:text-purple-300 font-medium">Контрактов</p>
              <p className="text-3xl font-bold text-purple-900 dark:text-purple-100 mt-1">
                {totalContracts}
              </p>
              <p className="text-xs text-purple-600 dark:text-purple-400 mt-1">
                обработано
              </p>
            </div>
            <div className="w-12 h-12 bg-purple-200 dark:bg-purple-900/50 rounded-lg flex items-center justify-center">
              <FileText className="text-purple-700 dark:text-purple-300" size={24} />
            </div>
          </div>
        </div>

        <div className="card bg-gradient-to-br from-yellow-50 to-yellow-100 dark:from-yellow-900/20 dark:to-yellow-800/20 border-yellow-200 dark:border-yellow-800">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-yellow-700 dark:text-yellow-300 font-medium">В ожидании</p>
              <p className="text-3xl font-bold text-yellow-900 dark:text-yellow-100 mt-1">
                {pendingContracts}
              </p>
              <p className="text-xs text-yellow-600 dark:text-yellow-400 mt-1">
                требуют проверки
              </p>
            </div>
            <div className="w-12 h-12 bg-yellow-200 dark:bg-yellow-900/50 rounded-lg flex items-center justify-center">
              <Clock className="text-yellow-700 dark:text-yellow-300" size={24} />
            </div>
          </div>
        </div>
      </div>

      {/* System Status */}
      <div className="card">
        <div className="flex items-center gap-3 mb-4">
          <Activity size={24} className="text-primary-600 dark:text-primary-400" />
          <h2 className="text-xl font-bold">Статус системы</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 bg-gray-50 dark:bg-dark-700 rounded-lg">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-600 dark:text-gray-400">Uptime</span>
              <CheckCircle className="text-green-500" size={20} />
            </div>
            <p className="text-2xl font-bold">99.9%</p>
            <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">
              За последние 30 дней
            </p>
          </div>

          <div className="p-4 bg-gray-50 dark:bg-dark-700 rounded-lg">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-600 dark:text-gray-400">Запросов/мин</span>
              <TrendingUp className="text-blue-500" size={20} />
            </div>
            <p className="text-2xl font-bold">45</p>
            <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">
              Средняя нагрузка
            </p>
          </div>

          <div className="p-4 bg-gray-50 dark:bg-dark-700 rounded-lg">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-600 dark:text-gray-400">Использование памяти</span>
              <HardDrive className="text-purple-500" size={20} />
            </div>
            <p className="text-2xl font-bold">256 MB</p>
            <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">
              из 512 MB доступно
            </p>
          </div>
        </div>
      </div>

      {/* Server Health */}
      <div className="card">
        <div className="flex items-center gap-3 mb-4">
          <Server size={24} className="text-primary-600 dark:text-primary-400" />
          <h2 className="text-xl font-bold">Здоровье серверов</h2>
        </div>

        <div className="space-y-3">
          {guilds?.slice(0, 5).map((guild: any) => (
            <div
              key={guild.guild_id}
              className="flex items-center justify-between p-4 bg-gray-50 dark:bg-dark-700 rounded-lg"
            >
              <div className="flex items-center gap-3">
                {guild.icon_url ? (
                  <img
                    src={guild.icon_url}
                    alt={guild.guild_name}
                    className="w-10 h-10 rounded-full"
                  />
                ) : (
                  <div className="w-10 h-10 rounded-full bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center">
                    <Server className="text-primary-600 dark:text-primary-400" size={20} />
                  </div>
                )}
                <div>
                  <h3 className="font-semibold">{guild.guild_name}</h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    {guild.total_users} пользователей • {guild.total_contracts} контрактов
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {guild.is_active ? (
                  <span className="flex items-center gap-1 text-sm text-green-600 dark:text-green-400">
                    <CheckCircle size={16} />
                    Активен
                  </span>
                ) : (
                  <span className="flex items-center gap-1 text-sm text-red-600 dark:text-red-400">
                    <AlertTriangle size={16} />
                    Неактивен
                  </span>
                )}
              </div>
            </div>
          ))}

          {totalGuilds > 5 && (
            <div className="text-center pt-2">
              <Link
                to="/"
                className="text-primary-600 dark:text-primary-400 hover:underline text-sm"
              >
                Показать все {totalGuilds} серверов →
              </Link>
            </div>
          )}
        </div>
      </div>

      {/* Database Management */}
      <div className="card">
        <div className="flex items-center gap-3 mb-4">
          <Database size={24} className="text-primary-600 dark:text-primary-400" />
          <h2 className="text-xl font-bold">Управление базой данных</h2>
        </div>

        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4 mb-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="text-yellow-600 dark:text-yellow-400 mt-0.5" size={20} />
            <div>
              <h3 className="font-semibold text-yellow-900 dark:text-yellow-100 mb-1">
                ⚠️ Внимание
              </h3>
              <p className="text-sm text-yellow-800 dark:text-yellow-200">
                Операции с базой данных могут привести к потере данных. Используйте с осторожностью.
              </p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <button className="btn btn-primary flex items-center justify-center gap-2">
            <Database size={20} />
            Создать бэкап
          </button>
          <button className="btn btn-secondary flex items-center justify-center gap-2">
            <Database size={20} />
            Восстановить из бэкапа
          </button>
          <button className="btn btn-secondary flex items-center justify-center gap-2 text-red-600 dark:text-red-400 border-red-200 dark:border-red-800 hover:bg-red-50 dark:hover:bg-red-900/20">
            <AlertTriangle size={20} />
            Очистить старые данные
          </button>
        </div>

        <div className="mt-4 p-4 bg-gray-50 dark:bg-dark-700 rounded-lg">
          <h3 className="font-semibold mb-2">Информация о базе</h3>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-gray-600 dark:text-gray-400">Размер БД</p>
              <p className="font-semibold">24.5 MB</p>
            </div>
            <div>
              <p className="text-gray-600 dark:text-gray-400">Последний бэкап</p>
              <p className="font-semibold">2 часа назад</p>
            </div>
            <div>
              <p className="text-gray-600 dark:text-gray-400">Всего записей</p>
              <p className="font-semibold">{totalContracts + totalUsers}</p>
            </div>
            <div>
              <p className="text-gray-600 dark:text-gray-400">Версия схемы</p>
              <p className="font-semibold">v2.0 (multi-guild)</p>
            </div>
          </div>
        </div>
      </div>

      {/* Global Settings */}
      <div className="card">
        <div className="flex items-center gap-3 mb-4">
          <Settings size={24} className="text-primary-600 dark:text-primary-400" />
          <h2 className="text-xl font-bold">Глобальные настройки</h2>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2">
              Интервал опроса Google Sheets (секунды)
            </label>
            <input
              type="number"
              defaultValue="60"
              className="input w-full max-w-xs"
              min="30"
              max="600"
            />
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              Как часто проверять Google Sheets на новые контракты
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">
              Максимум серверов
            </label>
            <input
              type="number"
              defaultValue="100"
              className="input w-full max-w-xs"
              min="1"
              max="1000"
            />
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              Максимальное количество серверов которые может обслуживать бот
            </p>
          </div>

          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="debug-mode"
              className="w-4 h-4"
            />
            <label htmlFor="debug-mode" className="text-sm font-medium">
              Режим отладки (Debug Mode)
            </label>
          </div>

          <div className="pt-4">
            <button className="btn btn-primary">
              Сохранить настройки
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

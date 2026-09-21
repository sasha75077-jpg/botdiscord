import { useQuery } from '@tanstack/react-query';
import { guildsApi, permissionsApi } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import { useParams } from 'react-router-dom';
import {
  Server,
  Users,
  FileText,
  Clock,
  Settings,
  Shield,
  Database,
  CheckCircle,
  XCircle,
  Link as LinkIcon
} from 'lucide-react';
import { Link } from 'react-router-dom';

export default function AdminDashboard() {
  const { user } = useAuthStore();
  const { guildId: paramGuildId } = useParams<{ guildId: string }>();
  const guildId = paramGuildId ?? user?.guild_id;

  // Получить информацию о сервере
  const { data: guild, isLoading: guildLoading } = useQuery({
    queryKey: ['guild', guildId],
    queryFn: async () => {
      if (!guildId) return null;
      const { data } = await guildsApi.get(guildId);
      return data;
    },
    enabled: !!guildId,
  });

  // Получить настройки
  const { data: settings, isLoading: settingsLoading } = useQuery({
    queryKey: ['guild-settings', guildId],
    queryFn: async () => {
      if (!guildId) return null;
      const { data } = await guildsApi.getSettings(guildId);
      return data;
    },
    enabled: !!guildId,
  });

  // Получить модули
  const { data: modules, isLoading: modulesLoading } = useQuery({
    queryKey: ['guild-modules', guildId],
    queryFn: async () => {
      if (!guildId) return null;
      const { data } = await guildsApi.getModules(guildId);
      return data;
    },
    enabled: !!guildId,
  });

  // Живой онлайн/состав из Discord
  const { data: live } = useQuery({
    queryKey: ['dashboard-live', guildId],
    queryFn: async () => {
      if (!guildId) return null;
      try {
        const { data } = await guildsApi.dashboard(guildId);
        return data;
      } catch {
        return null;
      }
    },
    enabled: !!guildId,
  });

  // Получить права доступа
  const { data: permissions, isLoading: permissionsLoading } = useQuery({
    queryKey: ['permissions', guildId],
    queryFn: async () => {
      if (!guildId) return null;
      const { data } = await permissionsApi.list(guildId);
      return data;
    },
    enabled: !!guildId,
  });

  if (guildLoading || settingsLoading || modulesLoading || permissionsLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
          <p className="mt-4 text-gray-600 dark:text-gray-400">Загрузка...</p>
        </div>
      </div>
    );
  }

  if (!guild) {
    return (
      <div className="text-center py-12">
        <Server className="mx-auto h-12 w-12 text-gray-400" />
        <p className="mt-4 text-gray-600 dark:text-gray-400">
          Сервер не найден
        </p>
      </div>
    );
  }

  const sheetsEnabled = settings?.settings?.sheets_enabled === 'True';
  const sheetId = settings?.settings?.sheet_id;
  const hasCredentials = settings?.settings?.credentials_path;

  // Подсчет ролей
  const adminCount = permissions?.permissions?.filter((p: any) => p.role === 'admin').length || 0;
  const recruiterCount = permissions?.permissions?.filter((p: any) => p.role === 'recruiter').length || 0;
  const userCount = permissions?.permissions?.filter((p: any) => p.role === 'user').length || 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          {guild.icon_url ? (
            <img
              src={guild.icon_url}
              alt={guild.guild_name}
              className="w-16 h-16 rounded-full"
            />
          ) : (
            <div className="w-16 h-16 rounded-full bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center">
              <Server className="text-primary-600 dark:text-primary-400" size={28} />
            </div>
          )}
          <div>
            <h1 className="text-3xl font-bold">{guild.guild_name}</h1>
            <p className="text-gray-600 dark:text-gray-400">
              Панель администратора
            </p>
          </div>
        </div>
        <Link
          to="/settings"
          className="btn btn-primary flex items-center gap-2"
        >
          <Settings size={20} />
          Настройки
        </Link>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Участников Discord</p>
              <p className="text-3xl font-bold mt-1">{live?.members_total ?? '—'}</p>
              <p className="text-xs text-green-600 dark:text-green-400 mt-1">
                Онлайн: {live?.members_online ?? '—'}
              </p>
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
              <p className="text-3xl font-bold mt-1">{guild.total_contracts}</p>
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
              <p className="text-3xl font-bold mt-1">{guild.pending_contracts}</p>
            </div>
            <div className="w-12 h-12 bg-yellow-100 dark:bg-yellow-900/30 rounded-lg flex items-center justify-center">
              <Clock className="text-yellow-600 dark:text-yellow-400" size={24} />
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Рекрутеров</p>
              <p className="text-3xl font-bold mt-1">{recruiterCount}</p>
            </div>
            <div className="w-12 h-12 bg-purple-100 dark:bg-purple-900/30 rounded-lg flex items-center justify-center">
              <Shield className="text-purple-600 dark:text-purple-400" size={24} />
            </div>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <Link
          to="/contracts"
          className="card hover:shadow-lg transition-shadow cursor-pointer"
        >
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-primary-100 dark:bg-primary-900/30 rounded-lg flex items-center justify-center">
              <FileText className="text-primary-600 dark:text-primary-400" size={24} />
            </div>
            <div>
              <h3 className="font-semibold text-lg">Контракты</h3>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Просмотр и управление
              </p>
            </div>
          </div>
        </Link>

        <Link
          to="/users"
          className="card hover:shadow-lg transition-shadow cursor-pointer"
        >
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
              <Users className="text-blue-600 dark:text-blue-400" size={24} />
            </div>
            <div>
              <h3 className="font-semibold text-lg">Пользователи</h3>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Управление ролями
              </p>
            </div>
          </div>
        </Link>

        <Link
          to="/reports"
          className="card hover:shadow-lg transition-shadow cursor-pointer"
        >
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center">
              <FileText className="text-green-600 dark:text-green-400" size={24} />
            </div>
            <div>
              <h3 className="font-semibold text-lg">Отчеты</h3>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Премии и повышения
              </p>
            </div>
          </div>
        </Link>
      </div>

      {/* Google Sheets Status */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold flex items-center gap-2">
            <Database size={24} />
            Google Sheets
          </h2>
          <Link
            to="/settings"
            className="text-sm text-primary-600 dark:text-primary-400 hover:underline"
          >
            Настроить
          </Link>
        </div>

        <div className="space-y-3">
          <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-dark-700 rounded-lg">
            <div className="flex items-center gap-3">
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                sheetsEnabled
                  ? 'bg-green-100 dark:bg-green-900/30'
                  : 'bg-gray-100 dark:bg-gray-900/30'
              }`}>
                {sheetsEnabled ? (
                  <CheckCircle className="text-green-600 dark:text-green-400" size={20} />
                ) : (
                  <XCircle className="text-gray-400" size={20} />
                )}
              </div>
              <div>
                <p className="font-medium">Статус импорта</p>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  {sheetsEnabled ? 'Включен' : 'Выключен'}
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-dark-700 rounded-lg">
            <div className="flex items-center gap-3">
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                hasCredentials
                  ? 'bg-green-100 dark:bg-green-900/30'
                  : 'bg-red-100 dark:bg-red-900/30'
              }`}>
                {hasCredentials ? (
                  <CheckCircle className="text-green-600 dark:text-green-400" size={20} />
                ) : (
                  <XCircle className="text-red-600 dark:text-red-400" size={20} />
                )}
              </div>
              <div>
                <p className="font-medium">Credentials</p>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  {hasCredentials ? 'Загружен' : 'Не загружен'}
                </p>
              </div>
            </div>
          </div>

          {sheetId && (
            <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-dark-700 rounded-lg">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
                  <LinkIcon className="text-blue-600 dark:text-blue-400" size={20} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium">Sheet ID</p>
                  <p className="text-sm text-gray-600 dark:text-gray-400 truncate">
                    {sheetId}
                  </p>
                </div>
              </div>
              <a
                href={`https://docs.google.com/spreadsheets/d/${sheetId}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary-600 dark:text-primary-400 hover:underline text-sm"
              >
                Открыть
              </a>
            </div>
          )}
        </div>

        <div className="mt-4">
          <Link
            to={`/guilds/${guildId}/sheets`}
            className="btn btn-primary text-sm"
          >
            Настроить Google Sheets
          </Link>
        </div>
      </div>

      {/* Roles Overview */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold flex items-center gap-2">
            <Shield size={24} />
            Роли и права доступа
          </h2>
          <Link
            to="/users"
            className="text-sm text-primary-600 dark:text-primary-400 hover:underline"
          >
            Управление
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 bg-gradient-to-br from-purple-50 to-purple-100 dark:from-purple-900/20 dark:to-purple-800/20 rounded-lg">
            <div className="flex items-center gap-3 mb-2">
              <Shield className="text-purple-600 dark:text-purple-400" size={20} />
              <h3 className="font-semibold">Администраторы</h3>
            </div>
            <p className="text-3xl font-bold text-purple-600 dark:text-purple-400">
              {adminCount}
            </p>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              Полный доступ к серверу
            </p>
          </div>

          <div className="p-4 bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900/20 dark:to-blue-800/20 rounded-lg">
            <div className="flex items-center gap-3 mb-2">
              <Users className="text-blue-600 dark:text-blue-400" size={20} />
              <h3 className="font-semibold">Рекрутеры</h3>
            </div>
            <p className="text-3xl font-bold text-blue-600 dark:text-blue-400">
              {recruiterCount}
            </p>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              Агитации и заявки
            </p>
          </div>

          <div className="p-4 bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900/20 dark:to-gray-800/20 rounded-lg">
            <div className="flex items-center gap-3 mb-2">
              <Users className="text-gray-600 dark:text-gray-400" size={20} />
              <h3 className="font-semibold">Пользователи</h3>
            </div>
            <p className="text-3xl font-bold text-gray-600 dark:text-gray-400">
              {userCount}
            </p>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              Базовый доступ
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { guildsApi } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import { Users, Wifi, Shield, FileText, CheckCircle, Clock, XCircle, Plus } from 'lucide-react';

export default function UserDashboard() {
  const { user } = useAuthStore();
  const guildId = user?.guild_id || '';

  const { data, isLoading } = useQuery({
    queryKey: ['dashboard', guildId],
    queryFn: async () => (await guildsApi.dashboard(guildId)).data,
    enabled: !!guildId,
  });

  const my = data?.my_contracts || { total: 0, approved: 0, pending: 0, rejected: 0 };
  const recent: any[] = data?.my_recent || [];

  const stat = (label: string, value: any, icon: any, color: string) => (
    <div className="card">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-600 dark:text-gray-400">{label}</p>
          <p className="text-3xl font-bold mt-1">{value ?? '—'}</p>
        </div>
        <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${color}`}>
          {icon}
        </div>
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold mb-2">{data?.guild_name || 'Мой дашборд'}</h1>
          <p className="text-gray-600 dark:text-gray-400">
            Моя статистика{data?.my_rank ? ` • Ранг: ${data.my_rank}` : ''}
          </p>
        </div>
        <Link to="/contracts/new" className="btn btn-primary flex items-center gap-2">
          <Plus size={18} /> Отправить контракт
        </Link>
      </div>

      {isLoading ? (
        <p className="text-gray-500">Загрузка...</p>
      ) : (
        <>
          <div>
            <h2 className="text-lg font-bold mb-3">Сервер</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {stat('Всего участников', data?.members_total,
                <Users size={24} className="text-blue-600 dark:text-blue-400" />,
                'bg-blue-100 dark:bg-blue-900/30')}
              {stat('Онлайн', data?.members_online,
                <Wifi size={24} className="text-green-600 dark:text-green-400" />,
                'bg-green-100 dark:bg-green-900/30')}
              {stat('Админов', data?.admins,
                <Shield size={24} className="text-purple-600 dark:text-purple-400" />,
                'bg-purple-100 dark:bg-purple-900/30')}
              {stat('Рекрутов', data?.recruiters,
                <Shield size={24} className="text-orange-600 dark:text-orange-400" />,
                'bg-orange-100 dark:bg-orange-900/30')}
            </div>
          </div>

          <div>
            <h2 className="text-lg font-bold mb-3">Мои контракты</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {stat('Всего', my.total,
                <FileText size={24} className="text-blue-600 dark:text-blue-400" />,
                'bg-blue-100 dark:bg-blue-900/30')}
              {stat('Выполнено', my.approved,
                <CheckCircle size={24} className="text-green-600 dark:text-green-400" />,
                'bg-green-100 dark:bg-green-900/30')}
              {stat('Ожидают', my.pending,
                <Clock size={24} className="text-yellow-600 dark:text-yellow-400" />,
                'bg-yellow-100 dark:bg-yellow-900/30')}
              {stat('Отклонено', my.rejected,
                <XCircle size={24} className="text-red-600 dark:text-red-400" />,
                'bg-red-100 dark:bg-red-900/30')}
            </div>
          </div>

          <div className="card">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-xl font-bold">Последние контракты</h2>
              <Link to="/contracts" className="text-sm text-primary-600 dark:text-primary-400 hover:underline">
                Все →
              </Link>
            </div>
            {recent.length === 0 ? (
              <p className="text-gray-500 text-sm">Пока пусто.</p>
            ) : (
              <div className="space-y-2">
                {recent.map((ct: any) => (
                  <Link key={ct.id} to={`/contracts/${ct.id}`} className="block">
                    <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-dark-700 rounded-lg hover:bg-gray-100 dark:hover:bg-dark-600">
                      <p className="font-medium">#{ct.id} • {ct.contract_type}{ct.price ? ` • ${ct.price}` : ''}</p>
                      <span className="text-xs text-gray-500">{ct.status} • {ct.created_at}</span>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

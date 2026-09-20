import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { contractsApi } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import { FileText, Plus, X } from 'lucide-react';

const STATUS_TABS = [
  { id: undefined, name: 'Все' },
  { id: 'pending', name: 'Ожидают' },
  { id: 'approved', name: 'Принятые' },
  { id: 'rejected', name: 'Отклоненные' },
];

export default function ContractsPage() {
  const { user } = useAuthStore();
  const guildId = user?.guild_id || '';
  const [tab, setTab] = useState<string | undefined>('pending');
  const [searchParams, setSearchParams] = useSearchParams();
  const filterUser = searchParams.get('user') || '';

  const { data, isLoading } = useQuery({
    queryKey: ['contracts', guildId, tab, filterUser],
    queryFn: async () => (await contractsApi.list(guildId, { status: tab, discord_id: filterUser || undefined })).data,
    enabled: !!guildId,
  });

  const contracts: any[] = Array.isArray(data) ? data : [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold flex items-center gap-2">
          <FileText size={28} /> {user?.role === 'user' || user?.role === 'recruiter' ? 'Мои контракты' : 'Контракты'}
        </h1>
        <Link to="/contracts/new" className="btn btn-primary flex items-center gap-2">
          <Plus size={18} /> Отправить
        </Link>
      </div>

      <div className="flex gap-2 flex-wrap">
        {STATUS_TABS.map((t) => (
          <button
            key={t.name}
            onClick={() => setTab(t.id)}
            className={`px-4 py-2 rounded-lg text-sm font-medium ${
              tab === t.id
                ? 'bg-primary-600 text-white'
                : 'bg-gray-100 dark:bg-dark-700 text-gray-700 dark:text-gray-300'
            }`}
          >
            {t.name}
          </button>
        ))}
        {filterUser && (
          <button
            onClick={() => setSearchParams({})}
            className="px-4 py-2 rounded-lg text-sm font-medium bg-gray-200 dark:bg-dark-600 flex items-center gap-1"
          >
            <X size={14} /> {filterUser}
          </button>
        )}
      </div>

      {isLoading ? (
        <p className="text-gray-500">Загрузка...</p>
      ) : contracts.length === 0 ? (
        <div className="card text-center py-12 text-gray-500">Контрактов нет.</div>
      ) : (
        <div className="space-y-3">
          {contracts.map((ct: any) => (
            <Link key={ct.id} to={`/contracts/${ct.id}`} className="block">
              <div className="card hover:shadow-lg transition-shadow flex items-center gap-4">
                <div className="flex-1 min-w-0">
                  <p className="font-semibold truncate">
                    #{ct.id} • {ct.contract_type}
                    {ct.price ? ` • ${ct.price}` : ''}
                  </p>
                  <p className="text-sm text-gray-500 truncate">
                    {ct.nickname || ct.discord_id} • {ct.created_at}
                  </p>
                </div>
                <span
                  className={`px-3 py-1 rounded-full text-xs font-medium flex-shrink-0 ${
                    ct.status === 'approved'
                      ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300'
                      : ct.status === 'rejected'
                        ? 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300'
                        : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300'
                  }`}
                >
                  {ct.status === 'approved' ? 'Принят' : ct.status === 'rejected' ? 'Отклонен' : 'Ожидает'}
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

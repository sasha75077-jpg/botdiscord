import { useAuthStore } from '@/store/authStore';
import ContractForm from '@/components/ContractForm';
import { FileText, ArrowLeft } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function NewContractPage() {
  const { user } = useAuthStore();
  const guildId = user?.guild_id || '';
  const isRecruiter = user?.role === 'recruiter';

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link
          to="/contracts"
          className="btn btn-secondary flex items-center gap-2"
        >
          <ArrowLeft size={20} />
          Назад
        </Link>
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 bg-primary-100 dark:bg-primary-900/30 rounded-lg flex items-center justify-center">
            <FileText className="text-primary-600 dark:text-primary-400" size={24} />
          </div>
          <div>
            <h1 className="text-3xl font-bold">
              {isRecruiter ? 'Отправить агитацию' : 'Новый контракт'}
            </h1>
            <p className="text-gray-600 dark:text-gray-400">
              {isRecruiter
                ? 'Агитации маркетплейс и WhatsApp News'
                : 'Заполните форму для отправки контракта'}
            </p>
          </div>
        </div>
      </div>

      {/* Info Cards for Recruiters */}
      {isRecruiter && (
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
          <h3 className="font-semibold text-blue-900 dark:text-blue-100 mb-2">
            📋 Доступные типы контрактов для рекрутеров
          </h3>
          <ul className="space-y-1 text-sm text-blue-800 dark:text-blue-200">
            <li>• <strong>Агитации - Маркетплейс</strong> — вставка ссылок на Discord маркетплейс</li>
            <li>• <strong>Агитации - WhatsApp News</strong> — скриншоты агитации в WN</li>
          </ul>
          <p className="mt-3 text-sm text-blue-700 dark:text-blue-300">
            💡 <strong>Важно:</strong> Укажите сумму за контракт при отправке
          </p>
        </div>
      )}

      {/* Form */}
      <div className="card">
        <ContractForm
          guildId={guildId}
          restrictedToAgitation={isRecruiter}
          onSuccess={() => {
            // Можно добавить редирект или уведомление
            window.location.href = '/contracts';
          }}
        />
      </div>
    </div>
  );
}

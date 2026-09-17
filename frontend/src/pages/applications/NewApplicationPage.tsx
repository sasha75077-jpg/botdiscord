import { useAuthStore } from '@/store/authStore';
import ApplicationForm from '@/components/ApplicationForm';
import { Users, ArrowLeft } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function NewApplicationPage() {
  const { user } = useAuthStore();
  const guildId = user?.guild_id || '';

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link
          to="/"
          className="btn btn-secondary flex items-center gap-2"
        >
          <ArrowLeft size={20} />
          Назад
        </Link>
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 bg-purple-100 dark:bg-purple-900/30 rounded-lg flex items-center justify-center">
            <Users className="text-purple-600 dark:text-purple-400" size={24} />
          </div>
          <div>
            <h1 className="text-3xl font-bold">Заявка на вступление</h1>
            <p className="text-gray-600 dark:text-gray-400">
              Заполните форму для вступления в семью
            </p>
          </div>
        </div>
      </div>

      {/* Form */}
      <div className="card">
        <ApplicationForm
          guildId={guildId}
          onSuccess={() => {
            // Редирект после успешной отправки
            setTimeout(() => {
              window.location.href = '/';
            }, 2000);
          }}
        />
      </div>
    </div>
  );
}

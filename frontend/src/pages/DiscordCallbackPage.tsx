import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { authApi } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import { Loader2 } from 'lucide-react';

export default function DiscordCallbackPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { login } = useAuthStore();
  const [error, setError] = useState('');

  useEffect(() => {
    const handleCallback = async () => {
      const code = searchParams.get('code');
      const state = searchParams.get('state');

      if (!code) {
        setError('Код авторизации не получен');
        setTimeout(() => navigate('/login'), 3000);
        return;
      }

      try {
        // Извлечь guild_id из state если есть
        const guildId = state?.startsWith('guild:') ? state.split(':')[1] : undefined;

        const { data } = await authApi.discordCallback(code, guildId);
        const userResponse = await authApi.getCurrentUser();

        login(data.access_token, data.refresh_token, userResponse.data);
        navigate('/');
      } catch (err: any) {
        console.error('Discord callback error:', err);
        setError(err.response?.data?.detail || 'Ошибка авторизации через Discord');
        setTimeout(() => navigate('/login'), 3000);
      }
    };

    handleCallback();
  }, [searchParams, login, navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-500 to-primary-700">
      <div className="card max-w-md w-full text-center">
        {!error ? (
          <>
            <Loader2 className="animate-spin mx-auto mb-4 text-primary-600" size={48} />
            <h2 className="text-2xl font-bold mb-2">Авторизация...</h2>
            <p className="text-gray-600 dark:text-gray-400">
              Пожалуйста, подождите
            </p>
          </>
        ) : (
          <>
            <div className="text-red-600 dark:text-red-400 mb-4 text-5xl">⚠️</div>
            <h2 className="text-2xl font-bold mb-2 text-red-600 dark:text-red-400">Ошибка</h2>
            <p className="text-gray-600 dark:text-gray-400 mb-4">{error}</p>
            <p className="text-sm text-gray-500">Перенаправление на страницу входа...</p>
          </>
        )}
      </div>
    </div>
  );
}

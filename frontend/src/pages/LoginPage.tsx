import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { authApi } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import { LogIn, User as UserIcon } from 'lucide-react';

export default function LoginPage() {
  const navigate = useNavigate();
  const { login } = useAuthStore();
  const [activeTab, setActiveTab] = useState<'owner' | 'discord'>('discord');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleOwnerLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const { data } = await authApi.ownerLogin(email, password);
      const userResponse = await authApi.getCurrentUser();

      login(data.access_token, data.refresh_token, userResponse.data);
      navigate('/');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка входа');
    } finally {
      setLoading(false);
    }
  };

  const handleDiscordLogin = async () => {
    setError('');
    setLoading(true);

    try {
      const { data } = await authApi.getDiscordOAuthUrl();
      window.location.href = data.url;
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка получения Discord OAuth URL');
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-500 to-primary-700 dark:from-dark-900 dark:to-dark-800 px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">Melancholia</h1>
          <p className="text-primary-100">Панель управления ботом</p>
        </div>

        <div className="card">
          {/* Tabs */}
          <div className="flex border-b border-gray-200 dark:border-dark-600 mb-6">
            <button
              onClick={() => setActiveTab('discord')}
              className={`flex-1 py-3 text-center font-medium transition-colors ${
                activeTab === 'discord'
                  ? 'border-b-2 border-primary-600 text-primary-600 dark:text-primary-400'
                  : 'text-gray-500 hover:text-gray-700 dark:text-gray-400'
              }`}
            >
              Discord
            </button>
            <button
              onClick={() => setActiveTab('owner')}
              className={`flex-1 py-3 text-center font-medium transition-colors ${
                activeTab === 'owner'
                  ? 'border-b-2 border-primary-600 text-primary-600 dark:text-primary-400'
                  : 'text-gray-500 hover:text-gray-700 dark:text-gray-400'
              }`}
            >
              Owner
            </button>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-100 dark:bg-red-900/30 border border-red-400 dark:border-red-800 text-red-700 dark:text-red-300 rounded-lg">
              {error}
            </div>
          )}

          {/* Discord Login */}
          {activeTab === 'discord' && (
            <div className="space-y-4">
              <p className="text-sm text-gray-600 dark:text-gray-400 text-center">
                Войдите через Discord для доступа к панели
              </p>
              <button
                onClick={handleDiscordLogin}
                disabled={loading}
                className="w-full btn btn-primary flex items-center justify-center gap-2"
              >
                <UserIcon size={20} />
                {loading ? 'Перенаправление...' : 'Войти через Discord'}
              </button>
            </div>
          )}

          {/* Owner Login */}
          {activeTab === 'owner' && (
            <form onSubmit={handleOwnerLogin} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="input"
                  placeholder="admin@example.com"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Пароль</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input"
                  placeholder="••••••••"
                  required
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full btn btn-primary flex items-center justify-center gap-2"
              >
                <LogIn size={20} />
                {loading ? 'Вход...' : 'Войти'}
              </button>
            </form>
          )}
        </div>

        <p className="text-center text-sm text-primary-100 mt-6">
          Версия 2.0.0 • {new Date().getFullYear()}
        </p>
      </div>
    </div>
  );
}

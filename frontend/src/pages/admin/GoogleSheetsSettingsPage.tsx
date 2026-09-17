import { useState, useEffect } from 'react';
import { useAuthStore } from '@/store/authStore';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { guildsApi } from '@/lib/api';
import {
  Database,
  Upload,
  CheckCircle,
  XCircle,
  AlertCircle,
  Link as LinkIcon,
  Loader,
  ArrowLeft,
} from 'lucide-react';
import { Link, useParams, useNavigate } from 'react-router-dom';

export default function GoogleSheetsSettingsPage() {
  const { guildId } = useParams<{ guildId: string }>();
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [sheetId, setSheetId] = useState('');
  const [credentialsFile, setCredentialsFile] = useState<File | null>(null);
  const [sheetsEnabled, setSheetsEnabled] = useState(false);
  const [testResult, setTestResult] = useState<any>(null);
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Получить текущие настройки
  const { data: settings, isLoading } = useQuery({
    queryKey: ['guild-settings', guildId],
    queryFn: async () => {
      if (!guildId) return null;
      const { data } = await guildsApi.getSettings(guildId);
      return data;
    },
    enabled: !!guildId,
  });

  // Update state when settings load
  useEffect(() => {
    if (settings?.settings) {
      setSheetId(settings.settings.sheet_id || '');
      setSheetsEnabled(settings.settings.sheets_enabled === 'True');
    }
  }, [settings]);

  // Получить информацию о сервере
  const { data: guild } = useQuery({
    queryKey: ['guild', guildId],
    queryFn: async () => {
      if (!guildId) return null;
      const { data } = await guildsApi.get(guildId);
      return data;
    },
    enabled: !!guildId,
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.endsWith('.json')) {
      setError('Файл должен быть в формате JSON');
      return;
    }

    setCredentialsFile(file);
    setError('');
  };

  const handleTestConnection = async () => {
    if (!sheetId.trim()) {
      setError('Введите Sheet ID');
      return;
    }

    setTesting(true);
    setError('');
    setTestResult(null);

    try {
      // Отправить запрос на тестирование подключения
      const response = await fetch(`/api/guilds/${guildId}/sheets/test`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('access_token')}`,
        },
        body: JSON.stringify({ sheet_id: sheetId }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Ошибка проверки подключения');
      }

      setTestResult(data);
    } catch (err: any) {
      setError(err.message || 'Произошла ошибка');
    } finally {
      setTesting(false);
    }
  };

  const handleSave = async () => {
    if (!sheetId.trim()) {
      setError('Введите Sheet ID');
      return;
    }

    setError('');
    setSuccess('');

    try {
      const formData = new FormData();
      formData.append('sheet_id', sheetId);
      formData.append('sheets_enabled', sheetsEnabled ? 'True' : 'False');

      if (credentialsFile) {
        formData.append('credentials', credentialsFile);
      }

      const response = await fetch(`/api/guilds/${guildId}/sheets/configure`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${localStorage.getItem('access_token')}`,
        },
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Ошибка сохранения настроек');
      }

      setSuccess('Настройки успешно сохранены!');
      queryClient.invalidateQueries({ queryKey: ['guild-settings', guildId] });

      // Редирект через 2 секунды
      setTimeout(() => {
        navigate(`/guilds/${guildId}`);
      }, 2000);
    } catch (err: any) {
      setError(err.message || 'Произошла ошибка');
    }
  };

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

  const hasCredentials = settings?.settings?.credentials_path;
  const currentSheetId = settings?.settings?.sheet_id;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link
          to={`/guilds/${guildId}`}
          className="btn btn-secondary flex items-center gap-2"
        >
          <ArrowLeft size={20} />
          Назад
        </Link>
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center">
            <Database className="text-green-600 dark:text-green-400" size={24} />
          </div>
          <div>
            <h1 className="text-3xl font-bold">Настройка Google Sheets</h1>
            <p className="text-gray-600 dark:text-gray-400">
              {guild?.guild_name || 'Сервер'}
            </p>
          </div>
        </div>
      </div>

      {/* Success/Error Messages */}
      {success && (
        <div className="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg flex items-center gap-3">
          <CheckCircle className="text-green-600 dark:text-green-400" size={20} />
          <p className="text-green-800 dark:text-green-200">{success}</p>
        </div>
      )}

      {error && (
        <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-center gap-3">
          <AlertCircle className="text-red-600 dark:text-red-400" size={20} />
          <p className="text-red-800 dark:text-red-200">{error}</p>
        </div>
      )}

      {/* Instructions */}
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
        <h3 className="font-semibold text-blue-900 dark:text-blue-100 mb-2">
          📋 Инструкция по настройке
        </h3>
        <ol className="space-y-2 text-sm text-blue-800 dark:text-blue-200">
          <li>1. Создайте Service Account в Google Cloud Console</li>
          <li>2. Скачайте JSON файл с credentials</li>
          <li>3. Загрузите его ниже</li>
          <li>4. Скопируйте ID вашей Google Sheets таблицы из URL</li>
          <li>5. Предоставьте доступ к таблице для Service Account email</li>
          <li>6. Проверьте подключение и сохраните</li>
        </ol>
        <p className="mt-3 text-sm text-blue-700 dark:text-blue-300">
          💡 <strong>Подсказка:</strong> Sheet ID находится в URL между /d/ и /edit
        </p>
      </div>

      {/* Step 1: Upload Credentials */}
      <div className="card">
        <div className="flex items-center gap-2 mb-4">
          <span className="flex items-center justify-center w-8 h-8 rounded-full bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400 font-bold">
            1
          </span>
          <h2 className="text-xl font-bold">Загрузите credentials.json</h2>
        </div>

        {hasCredentials && !credentialsFile && (
          <div className="mb-4 p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg flex items-center gap-2">
            <CheckCircle className="text-green-600 dark:text-green-400" size={20} />
            <span className="text-sm text-green-800 dark:text-green-200">
              Credentials файл уже загружен
            </span>
          </div>
        )}

        <div className="border-2 border-dashed border-gray-300 dark:border-gray-700 rounded-lg p-6 text-center">
          <Upload className="mx-auto h-12 w-12 text-gray-400 mb-3" />
          <label className="cursor-pointer">
            <span className="text-primary-600 dark:text-primary-400 hover:underline">
              Выберите файл
            </span>
            <span className="text-gray-600 dark:text-gray-400"> или перетащите сюда</span>
            <input
              type="file"
              accept=".json"
              onChange={handleFileChange}
              className="hidden"
            />
          </label>
          <p className="text-sm text-gray-500 dark:text-gray-500 mt-2">
            credentials.json от Google Service Account
          </p>
        </div>

        {credentialsFile && (
          <div className="mt-4 p-3 bg-gray-50 dark:bg-dark-700 rounded-lg flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CheckCircle className="text-green-600 dark:text-green-400" size={20} />
              <span className="text-sm font-medium">{credentialsFile.name}</span>
            </div>
            <button
              onClick={() => setCredentialsFile(null)}
              className="text-sm text-red-600 dark:text-red-400 hover:underline"
            >
              Удалить
            </button>
          </div>
        )}
      </div>

      {/* Step 2: Sheet ID */}
      <div className="card">
        <div className="flex items-center gap-2 mb-4">
          <span className="flex items-center justify-center w-8 h-8 rounded-full bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400 font-bold">
            2
          </span>
          <h2 className="text-xl font-bold">Введите Sheet ID</h2>
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">
            Sheet ID <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            value={sheetId}
            onChange={(e) => setSheetId(e.target.value)}
            className="input w-full"
            placeholder="1BxiMVs0XRA5nFMdx..."
          />
          {currentSheetId && sheetId === currentSheetId && (
            <div className="mt-2 flex items-center gap-2">
              <LinkIcon className="text-primary-600 dark:text-primary-400" size={16} />
              <a
                href={`https://docs.google.com/spreadsheets/d/${currentSheetId}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-primary-600 dark:text-primary-400 hover:underline"
              >
                Открыть текущую таблицу
              </a>
            </div>
          )}
        </div>

        <div className="mt-4">
          <button
            onClick={handleTestConnection}
            disabled={testing || !sheetId.trim()}
            className="btn btn-secondary flex items-center gap-2"
          >
            {testing ? (
              <>
                <Loader className="animate-spin" size={20} />
                Проверка...
              </>
            ) : (
              <>
                <CheckCircle size={20} />
                Проверить подключение
              </>
            )}
          </button>
        </div>
      </div>

      {/* Step 3: Test Result */}
      {testResult && (
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <span className="flex items-center justify-center w-8 h-8 rounded-full bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400 font-bold">
              3
            </span>
            <h2 className="text-xl font-bold">Результат проверки</h2>
          </div>

          {testResult.ok ? (
            <div className="space-y-3">
              <div className="p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg flex items-center gap-2">
                <CheckCircle className="text-green-600 dark:text-green-400" size={20} />
                <span className="text-green-800 dark:text-green-200 font-medium">
                  Подключение успешно!
                </span>
              </div>

              {testResult.title && (
                <div className="p-3 bg-gray-50 dark:bg-dark-700 rounded-lg">
                  <p className="text-sm text-gray-600 dark:text-gray-400">Название таблицы</p>
                  <p className="font-semibold">{testResult.title}</p>
                </div>
              )}

              {testResult.sheets && testResult.sheets.length > 0 && (
                <div className="p-3 bg-gray-50 dark:bg-dark-700 rounded-lg">
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">Листы в таблице</p>
                  <ul className="space-y-1">
                    {testResult.sheets.map((sheet: any, index: number) => (
                      <li key={index} className="text-sm">
                        • {sheet.name} ({sheet.rows || 0} строк)
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-center gap-2">
              <XCircle className="text-red-600 dark:text-red-400" size={20} />
              <span className="text-red-800 dark:text-red-200">
                {testResult.error || 'Ошибка подключения'}
              </span>
            </div>
          )}
        </div>
      )}

      {/* Step 4: Enable Import */}
      <div className="card">
        <div className="flex items-center gap-2 mb-4">
          <span className="flex items-center justify-center w-8 h-8 rounded-full bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400 font-bold">
            4
          </span>
          <h2 className="text-xl font-bold">Включить импорт</h2>
        </div>

        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="sheets-enabled"
              checked={sheetsEnabled}
              onChange={(e) => setSheetsEnabled(e.target.checked)}
              className="w-4 h-4"
            />
            <label htmlFor="sheets-enabled" className="text-sm font-medium">
              Автоматически импортировать контракты из Google Sheets
            </label>
          </div>

          <p className="text-sm text-gray-600 dark:text-gray-400">
            Интервал опроса настраивается в глобальных настройках бота (Owner Panel)
          </p>
        </div>
      </div>

      {/* Save Button */}
      <div className="flex gap-4">
        <button
          onClick={handleSave}
          disabled={!sheetId.trim()}
          className="btn btn-primary flex-1"
        >
          💾 Сохранить настройки
        </button>
        <Link to={`/guilds/${guildId}`} className="btn btn-secondary">
          Отмена
        </Link>
      </div>
    </div>
  );
}

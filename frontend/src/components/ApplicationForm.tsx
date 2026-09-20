import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { AlertCircle, CheckCircle, Users } from 'lucide-react';
import { applicationsApi, guildsApi } from '@/lib/api';

interface ApplicationFormProps {
  guildId: string;
  onSuccess?: () => void;
}

export interface Question {
  id: string;
  label: string;
  required?: boolean;
  min?: number;
}

export const DEFAULT_QUESTIONS: Question[] = [
  { id: 'nickname', label: 'Игровой никнейм', required: true },
  { id: 'age', label: 'Возраст', required: true },
  { id: 'experience', label: 'Опыт в игре', required: true },
  { id: 'reason', label: 'Почему хотите вступить', required: true, min: 20 },
];

export default function ApplicationForm({ guildId, onSuccess }: ApplicationFormProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [answers, setAnswers] = useState<Record<string, string>>({});

  const { data: settings } = useQuery({
    queryKey: ['guild-settings', guildId],
    queryFn: async () => (await guildsApi.getSettings(guildId)).data,
    enabled: !!guildId,
  });

  let questions: Question[] = DEFAULT_QUESTIONS;
  try {
    const raw = settings?.settings?.application_questions;
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed) && parsed.length > 0) questions = parsed;
    }
  } catch { /* ignore */ }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess(false);
    setLoading(true);

    try {
      await applicationsApi.create(guildId, answers);
      setSuccess(true);
      setAnswers({});
      if (onSuccess) onSuccess();
    } catch (err: any) {
      setError(err.response?.data?.error || err.response?.data?.detail || 'Ошибка отправки заявки');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {success && (
        <div className="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg flex items-center gap-3">
          <CheckCircle className="text-green-600 dark:text-green-400" size={20} />
          <div>
            <p className="text-green-800 dark:text-green-200 font-medium">Заявка успешно отправлена!</p>
            <p className="text-sm text-green-700 dark:text-green-300 mt-1">Ожидайте рассмотрения администрацией</p>
          </div>
        </div>
      )}

      {error && (
        <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-center gap-3">
          <AlertCircle className="text-red-600 dark:text-red-400" size={20} />
          <p className="text-red-800 dark:text-red-200">{error}</p>
        </div>
      )}

      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <Users className="text-blue-600 dark:text-blue-400 mt-0.5" size={20} />
          <p className="text-sm text-blue-800 dark:text-blue-200">
            Заполни все обязательные поля. Администрация рассмотрит заявку в течение 24-48 часов.
          </p>
        </div>
      </div>

      {questions.map((q) => (
        <div key={q.id}>
          <label className="block text-sm font-medium mb-2">
            {q.label} {q.required && <span className="text-red-500">*</span>}
          </label>
          <textarea
            value={answers[q.id] || ''}
            onChange={(e) => setAnswers((a) => ({ ...a, [q.id]: e.target.value }))}
            className="input w-full min-h-[80px]"
            placeholder={q.label}
            required={q.required}
          />
          {q.min ? (
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              Минимум {q.min} символов. Текущее: {(answers[q.id] || '').length}
            </p>
          ) : null}
        </div>
      ))}

      <button type="submit" disabled={loading} className="btn btn-primary flex-1 w-full">
        {loading ? 'Отправка...' : 'Отправить заявку'}
      </button>
    </form>
  );
}

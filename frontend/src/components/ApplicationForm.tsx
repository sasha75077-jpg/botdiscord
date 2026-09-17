import { useState } from 'react';
import { useAuthStore } from '@/store/authStore';
import { Upload, X, AlertCircle, CheckCircle, Users } from 'lucide-react';

interface ApplicationFormProps {
  guildId: string;
  onSuccess?: () => void;
}

interface FileWithPreview {
  file: File;
  preview: string;
}

export default function ApplicationForm({ guildId, onSuccess }: ApplicationFormProps) {
  const { user } = useAuthStore();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  // Форма
  const [gameNickname, setGameNickname] = useState('');
  const [age, setAge] = useState('');
  const [experience, setExperience] = useState('');
  const [whyJoin, setWhyJoin] = useState('');
  const [referral, setReferral] = useState('');
  const [screenshots, setScreenshots] = useState<FileWithPreview[]>([]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files) return;

    const newFiles = Array.from(e.target.files).map(file => ({
      file,
      preview: URL.createObjectURL(file),
    }));

    setScreenshots(prev => [...prev, ...newFiles]);
  };

  const removeFile = (index: number) => {
    setScreenshots(prev => {
      const updated = [...prev];
      URL.revokeObjectURL(updated[index].preview);
      updated.splice(index, 1);
      return updated;
    });
  };

  const validateForm = (): string | null => {
    if (!gameNickname.trim()) return 'Укажите игровой никнейм';
    if (!age.trim()) return 'Укажите возраст';
    const ageNum = Number(age);
    if (!ageNum || ageNum < 10 || ageNum > 100) return 'Возраст должен быть от 10 до 100';
    if (!experience.trim()) return 'Укажите опыт в игре';
    if (!whyJoin.trim()) return 'Укажите причину вступления';
    if (whyJoin.length < 20) return 'Причина вступления должна быть минимум 20 символов';
    if (screenshots.length < 1) return 'Прикрепите хотя бы 1 скриншот';
    if (screenshots.length > 5) return 'Максимум 5 скриншотов';
    return null;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess(false);

    const validationError = validateForm();
    if (validationError) {
      setError(validationError);
      return;
    }

    setLoading(true);

    try {
      const formData = new FormData();

      // Payload
      const payload = {
        discordId: user?.discord_id,
        username: user?.username || '',
        gameNickname,
        age: Number(age),
        experience,
        whyJoin,
        referral: referral.trim() || null,
        submittedAt: new Date().toISOString(),
      };

      formData.append('payload', JSON.stringify(payload));
      formData.append('files_count', String(screenshots.length));

      // Добавить файлы
      for (let i = 0; i < screenshots.length; i++) {
        const { file } = screenshots[i];
        const reader = new FileReader();

        await new Promise<void>((resolve, reject) => {
          reader.onload = () => {
            const base64 = (reader.result as string).split(',')[1];
            formData.append(`file_${i}_base64`, base64);
            formData.append(`file_${i}_filename`, file.name);
            formData.append(`file_${i}_mime`, file.type);
            resolve();
          };
          reader.onerror = reject;
          reader.readAsDataURL(file);
        });
      }

      // Отправить через backend API
      const response = await fetch(`/api/guilds/${guildId}/applications/create`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Ошибка отправки заявки');
      }

      setSuccess(true);
      // Очистить форму
      setGameNickname('');
      setAge('');
      setExperience('');
      setWhyJoin('');
      setReferral('');
      setScreenshots([]);

      if (onSuccess) onSuccess();
    } catch (err: any) {
      setError(err.message || 'Произошла ошибка');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Success/Error Messages */}
      {success && (
        <div className="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg flex items-center gap-3">
          <CheckCircle className="text-green-600 dark:text-green-400" size={20} />
          <div>
            <p className="text-green-800 dark:text-green-200 font-medium">
              Заявка успешно отправлена!
            </p>
            <p className="text-sm text-green-700 dark:text-green-300 mt-1">
              Ожидайте рассмотрения администрацией
            </p>
          </div>
        </div>
      )}

      {error && (
        <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-center gap-3">
          <AlertCircle className="text-red-600 dark:text-red-400" size={20} />
          <p className="text-red-800 dark:text-red-200">{error}</p>
        </div>
      )}

      {/* Info Card */}
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <Users className="text-blue-600 dark:text-blue-400 mt-0.5" size={20} />
          <div className="flex-1">
            <h3 className="font-semibold text-blue-900 dark:text-blue-100 mb-2">
              📋 О заявке в семью
            </h3>
            <ul className="space-y-1 text-sm text-blue-800 dark:text-blue-200">
              <li>• Заполните все поля формы честно и подробно</li>
              <li>• Прикрепите скриншоты вашего профиля/достижений (1-5 штук)</li>
              <li>• Администрация рассмотрит заявку в течение 24-48 часов</li>
              <li>• Вы получите уведомление о результате в Discord</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Discord Username (Auto) */}
      <div>
        <label className="block text-sm font-medium mb-2">
          Discord пользователь
        </label>
        <input
          type="text"
          value={user?.username || 'Неизвестно'}
          className="input w-full bg-gray-100 dark:bg-gray-800"
          disabled
        />
        <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
          Определяется автоматически
        </p>
      </div>

      {/* Game Nickname */}
      <div>
        <label className="block text-sm font-medium mb-2">
          Игровой никнейм <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          value={gameNickname}
          onChange={(e) => setGameNickname(e.target.value)}
          className="input w-full"
          placeholder="Ваш ник в игре"
          required
        />
      </div>

      {/* Age */}
      <div>
        <label className="block text-sm font-medium mb-2">
          Возраст <span className="text-red-500">*</span>
        </label>
        <input
          type="number"
          value={age}
          onChange={(e) => setAge(e.target.value)}
          className="input w-full"
          placeholder="Полных лет"
          min="10"
          max="100"
          required
        />
      </div>

      {/* Experience */}
      <div>
        <label className="block text-sm font-medium mb-2">
          Опыт в игре <span className="text-red-500">*</span>
        </label>
        <textarea
          value={experience}
          onChange={(e) => setExperience(e.target.value)}
          className="input w-full min-h-[100px]"
          placeholder="Расскажите о вашем опыте: сколько играете, какие достижения, какие роли играли и т.д."
          required
        />
        <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
          Чем подробнее, тем лучше
        </p>
      </div>

      {/* Why Join */}
      <div>
        <label className="block text-sm font-medium mb-2">
          Почему хотите вступить в семью? <span className="text-red-500">*</span>
        </label>
        <textarea
          value={whyJoin}
          onChange={(e) => setWhyJoin(e.target.value)}
          className="input w-full min-h-[120px]"
          placeholder="Расскажите почему вы хотите присоединиться к нашей семье, что вас привлекло, чем можете быть полезны..."
          required
        />
        <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
          Минимум 20 символов. Текущее: {whyJoin.length}
        </p>
      </div>

      {/* Referral */}
      <div>
        <label className="block text-sm font-medium mb-2">
          Рекомендации (необязательно)
        </label>
        <input
          type="text"
          value={referral}
          onChange={(e) => setReferral(e.target.value)}
          className="input w-full"
          placeholder="Кто вас рекомендовал или пригласил"
        />
        <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
          Если кто-то из участников семьи вас пригласил, укажите его ник
        </p>
      </div>

      {/* Screenshots */}
      <div>
        <label className="block text-sm font-medium mb-2">
          Скриншоты <span className="text-red-500">*</span>
        </label>

        <div className="border-2 border-dashed border-gray-300 dark:border-gray-700 rounded-lg p-6 text-center">
          <Upload className="mx-auto h-12 w-12 text-gray-400 mb-3" />
          <label className="cursor-pointer">
            <span className="text-primary-600 dark:text-primary-400 hover:underline">
              Выберите файлы
            </span>
            <span className="text-gray-600 dark:text-gray-400"> или перетащите сюда</span>
            <input
              type="file"
              accept="image/*"
              multiple
              onChange={handleFileChange}
              className="hidden"
            />
          </label>
          <p className="text-sm text-gray-500 dark:text-gray-500 mt-2">
            1-5 скриншотов профиля/достижений (PNG, JPG до 8MB)
          </p>
        </div>

        {screenshots.length > 0 && (
          <div className="mt-4 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
            {screenshots.map((screenshot, index) => (
              <div key={index} className="relative group">
                <img
                  src={screenshot.preview}
                  alt={`Preview ${index + 1}`}
                  className="w-full h-32 object-cover rounded-lg"
                />
                <button
                  type="button"
                  onClick={() => removeFile(index)}
                  className="absolute top-2 right-2 bg-red-500 text-white p-1 rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  <X size={16} />
                </button>
                <div className="absolute bottom-2 left-2 right-2 bg-black/50 text-white text-xs text-center py-1 rounded">
                  {index + 1} / {screenshots.length}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Submit Button */}
      <div className="flex gap-4">
        <button
          type="submit"
          disabled={loading}
          className="btn btn-primary flex-1"
        >
          {loading ? 'Отправка...' : 'Отправить заявку'}
        </button>
      </div>

      {/* Footer Note */}
      <div className="text-sm text-gray-600 dark:text-gray-400 text-center p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
        <p>
          <strong>Примечание:</strong> После отправки заявки вы не сможете её отредактировать.
          Убедитесь что все данные указаны верно.
        </p>
      </div>
    </form>
  );
}

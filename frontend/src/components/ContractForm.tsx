import { useState } from 'react';
import { useAuthStore } from '@/store/authStore';
import { Upload, X, AlertCircle, CheckCircle } from 'lucide-react';

interface ContractFormProps {
  guildId: string;
  onSuccess?: () => void;
  restrictedToAgitation?: boolean; // true для recruiter
}

interface FileWithPreview {
  file: File;
  preview: string;
  role?: string;
}

const CONTRACT_TYPES = [
  { value: 'активация', label: 'Активация', recruiterOnly: false },
  { value: 'дары-моря', label: 'Дары моря', recruiterOnly: false },
  { value: 'металлургия-сдача', label: 'Металлургия - Сдача', recruiterOnly: false },
  { value: 'металлургия-добыча', label: 'Металлургия - Добыча', recruiterOnly: false },
  { value: 'товары', label: 'Товары', recruiterOnly: false },
  { value: 'ателье', label: 'Ателье', recruiterOnly: false },
  { value: 'агитации-маркетплейс', label: 'Агитации - Маркетплейс', recruiterOnly: true },
  { value: 'агитации-wn', label: 'Агитации - WhatsApp News', recruiterOnly: true },
  { value: 'тюнинг', label: 'Тюнинг', recruiterOnly: false },
];

export default function ContractForm({ guildId, onSuccess, restrictedToAgitation = false }: ContractFormProps) {
  const { user } = useAuthStore();
  const [contractType, setContractType] = useState('');
  const [files, setFiles] = useState<FileWithPreview[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  // Поля для разных типов контрактов
  const [price, setPrice] = useState('');
  const [fishType, setFishType] = useState('');
  const [fishQty, setFishQty] = useState('');
  const [oreType, setOreType] = useState('Железная руда');
  const [iron, setIron] = useState('');
  const [silver, setSilver] = useState('');
  const [copper, setCopper] = useState('');
  const [tin, setTin] = useState('');
  const [gold, setGold] = useState('');
  const [totalUniforms, setTotalUniforms] = useState('');
  const [links, setLinks] = useState(['']);
  const [wnCategory, setWnCategory] = useState('Зеленка(чат)');

  const availableTypes = restrictedToAgitation
    ? CONTRACT_TYPES.filter(t => t.recruiterOnly)
    : CONTRACT_TYPES;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files) return;

    const newFiles = Array.from(e.target.files).map(file => ({
      file,
      preview: URL.createObjectURL(file),
      role: contractType === 'товары' ? 'delivery' : undefined,
    }));

    setFiles(prev => [...prev, ...newFiles]);
  };

  const removeFile = (index: number) => {
    setFiles(prev => {
      const updated = [...prev];
      URL.revokeObjectURL(updated[index].preview);
      updated.splice(index, 1);
      return updated;
    });
  };

  const addLink = () => {
    setLinks(prev => [...prev, '']);
  };

  const updateLink = (index: number, value: string) => {
    setLinks(prev => {
      const updated = [...prev];
      updated[index] = value;
      return updated;
    });
  };

  const removeLink = (index: number) => {
    setLinks(prev => prev.filter((_, i) => i !== index));
  };

  const validateForm = (): string | null => {
    if (!contractType) return 'Выберите тип контракта';

    const n = files.length;

    switch (contractType) {
      case 'активация': {
        const priceNum = Number(price);
        if (!priceNum || priceNum <= 0) return 'Укажите сумму (целое число > 0)';
        if (priceNum > 20000) return 'Сумма не должна превышать 20000';
        if (n !== 1) return 'Можно прикрепить только 1 скриншот';
        break;
      }
      case 'дары-моря': {
        if (!fishType.trim()) return 'Укажите вид рыбы';
        const qty = Number(fishQty);
        if (!qty || qty <= 0) return 'Укажите количество (целое число > 0)';
        if (n < 1 || n > 10) return 'Нужно 1..10 скриншотов';
        break;
      }
      case 'металлургия-сдача': {
        if (!oreType) return 'Выберите руду';
        if (n !== 1) return 'Можно прикрепить только 1 скриншот';
        break;
      }
      case 'металлургия-добыча': {
        const hasAny = [iron, silver, copper, tin, gold].some(v => Number(v) > 0);
        if (!hasAny) return 'Укажите количество хотя бы для одного ресурса';
        if (n < 1 || n > 10) return 'Нужно 1..10 скриншотов';
        break;
      }
      case 'товары': {
        if (n < 1 || n > 2) return 'Можно 1 или 2 скриншота';
        break;
      }
      case 'ателье': {
        const total = Number(totalUniforms);
        if (!total || total <= 0) return 'Укажите общее количество (целое число > 0)';
        if (n < 1 || n > 10) return 'Нужно 1..10 скриншотов';
        break;
      }
      case 'агитации-маркетплейс': {
        const validLinks = links.filter(l => l.trim());
        if (validLinks.length < 1) return 'Вставьте хотя бы 1 ссылку';
        if (restrictedToAgitation && !price) return 'Укажите сумму за контракт';
        if (n > 0) return 'Скриншоты не требуются';
        break;
      }
      case 'агитации-wn': {
        if (!wnCategory) return 'Выберите категорию';
        if (restrictedToAgitation && !price) return 'Укажите сумму за контракт';
        if (n < 1 || n > 10) return 'Нужно 1..10 скриншотов';
        break;
      }
      case 'тюнинг': {
        if (n !== 1) return 'Можно прикрепить только 1 скриншот';
        break;
      }
    }

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
      const payload: any = {
        discordId: user?.discord_id,
        contractType,
        fields: {},
      };

      // Заполнить поля в зависимости от типа
      switch (contractType) {
        case 'активация':
          payload.fields.price = Number(price);
          break;
        case 'дары-моря':
          payload.fields.fishType = fishType;
          payload.fields.fishQty = Number(fishQty);
          break;
        case 'металлургия-сдача':
          payload.fields.oreType = oreType;
          break;
        case 'металлургия-добыча':
          payload.fields.iron = Number(iron) || 0;
          payload.fields.silver = Number(silver) || 0;
          payload.fields.copper = Number(copper) || 0;
          payload.fields.tin = Number(tin) || 0;
          payload.fields.gold = Number(gold) || 0;
          break;
        case 'ателье':
          payload.fields.totalUniforms = Number(totalUniforms);
          break;
        case 'агитации-маркетплейс':
          payload.fields.links = links.filter(l => l.trim());
          if (restrictedToAgitation) {
            payload.fields.price = Number(price);
          }
          break;
        case 'агитации-wn':
          payload.fields.category = wnCategory;
          if (restrictedToAgitation) {
            payload.fields.price = Number(price);
          }
          break;
      }

      formData.append('payload', JSON.stringify(payload));
      formData.append('files_count', String(files.length));

      // Добавить файлы
      for (let i = 0; i < files.length; i++) {
        const { file, role } = files[i];
        const reader = new FileReader();

        await new Promise<void>((resolve, reject) => {
          reader.onload = () => {
            const base64 = (reader.result as string).split(',')[1];
            formData.append(`file_${i}_base64`, base64);
            formData.append(`file_${i}_filename`, file.name);
            formData.append(`file_${i}_mime`, file.type);
            if (role) formData.append(`file_${i}_role`, role);
            resolve();
          };
          reader.onerror = reject;
          reader.readAsDataURL(file);
        });
      }

      // Отправить через backend API
      const response = await fetch(`/api/guilds/${guildId}/contracts/create`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Ошибка отправки контракта');
      }

      setSuccess(true);
      // Очистить форму
      setContractType('');
      setFiles([]);
      setPrice('');
      setFishType('');
      setFishQty('');
      setIron('');
      setSilver('');
      setCopper('');
      setTin('');
      setGold('');
      setTotalUniforms('');
      setLinks(['']);

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
          <p className="text-green-800 dark:text-green-200">
            Контракт успешно отправлен!
          </p>
        </div>
      )}

      {error && (
        <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-center gap-3">
          <AlertCircle className="text-red-600 dark:text-red-400" size={20} />
          <p className="text-red-800 dark:text-red-200">{error}</p>
        </div>
      )}

      {/* Contract Type */}
      <div>
        <label className="block text-sm font-medium mb-2">
          Тип контракта <span className="text-red-500">*</span>
        </label>
        <select
          value={contractType}
          onChange={(e) => setContractType(e.target.value)}
          className="input w-full"
          required
        >
          <option value="">Выберите тип контракта</option>
          {availableTypes.map(type => (
            <option key={type.value} value={type.value}>
              {type.label}
            </option>
          ))}
        </select>
      </div>

      {/* Dynamic Fields Based on Contract Type */}
      {contractType === 'активация' && (
        <div>
          <label className="block text-sm font-medium mb-2">
            Сумма <span className="text-red-500">*</span>
          </label>
          <input
            type="number"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            className="input w-full"
            placeholder="Введите сумму (до 20000)"
            min="1"
            max="20000"
            required
          />
        </div>
      )}

      {contractType === 'дары-моря' && (
        <>
          <div>
            <label className="block text-sm font-medium mb-2">
              Вид рыбы <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={fishType}
              onChange={(e) => setFishType(e.target.value)}
              className="input w-full"
              placeholder="Например: Лосось"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">
              Количество <span className="text-red-500">*</span>
            </label>
            <input
              type="number"
              value={fishQty}
              onChange={(e) => setFishQty(e.target.value)}
              className="input w-full"
              placeholder="Введите количество"
              min="1"
              required
            />
          </div>
        </>
      )}

      {contractType === 'металлургия-сдача' && (
        <div>
          <label className="block text-sm font-medium mb-2">
            Руда <span className="text-red-500">*</span>
          </label>
          <select
            value={oreType}
            onChange={(e) => setOreType(e.target.value)}
            className="input w-full"
            required
          >
            <option value="Железная руда">Железная руда</option>
            <option value="Серебряная руда">Серебряная руда</option>
            <option value="Медная руда">Медная руда</option>
            <option value="Оловянная руда">Оловянная руда</option>
            <option value="Золотая руда">Золотая руда</option>
          </select>
        </div>
      )}

      {contractType === 'металлургия-добыча' && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div>
            <label className="block text-sm font-medium mb-2">Железо</label>
            <input
              type="number"
              value={iron}
              onChange={(e) => setIron(e.target.value)}
              className="input w-full"
              min="0"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">Серебро</label>
            <input
              type="number"
              value={silver}
              onChange={(e) => setSilver(e.target.value)}
              className="input w-full"
              min="0"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">Медь</label>
            <input
              type="number"
              value={copper}
              onChange={(e) => setCopper(e.target.value)}
              className="input w-full"
              min="0"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">Олово</label>
            <input
              type="number"
              value={tin}
              onChange={(e) => setTin(e.target.value)}
              className="input w-full"
              min="0"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">Золото</label>
            <input
              type="number"
              value={gold}
              onChange={(e) => setGold(e.target.value)}
              className="input w-full"
              min="0"
            />
          </div>
        </div>
      )}

      {contractType === 'ателье' && (
        <div>
          <label className="block text-sm font-medium mb-2">
            Нашито форм (всего) <span className="text-red-500">*</span>
          </label>
          <input
            type="number"
            value={totalUniforms}
            onChange={(e) => setTotalUniforms(e.target.value)}
            className="input w-full"
            placeholder="Введите количество"
            min="1"
            required
          />
        </div>
      )}

      {contractType === 'агитации-маркетплейс' && (
        <>
          {restrictedToAgitation && (
            <div>
              <label className="block text-sm font-medium mb-2">
                Сумма за контракт <span className="text-red-500">*</span>
              </label>
              <input
                type="number"
                value={price}
                onChange={(e) => setPrice(e.target.value)}
                className="input w-full"
                placeholder="Укажите стоимость этого контракта"
                min="1"
                required
              />
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                💡 Укажите сумму за этот контракт агитации
              </p>
            </div>
          )}
          <div>
            <label className="block text-sm font-medium mb-2">
              Ссылки Discord маркетплейс <span className="text-red-500">*</span>
            </label>
            {links.map((link, index) => (
              <div key={index} className="flex gap-2 mb-2">
                <input
                  type="url"
                  value={link}
                  onChange={(e) => updateLink(index, e.target.value)}
                  className="input flex-1"
                  placeholder="https://discord.com/..."
                />
                {links.length > 1 && (
                  <button
                    type="button"
                    onClick={() => removeLink(index)}
                    className="btn btn-secondary"
                  >
                    <X size={20} />
                  </button>
                )}
              </div>
            ))}
            <button
              type="button"
              onClick={addLink}
              className="btn btn-secondary text-sm"
            >
              + Добавить ссылку
            </button>
          </div>
        </>
      )}

      {contractType === 'агитации-wn' && (
        <>
          {restrictedToAgitation && (
            <div>
              <label className="block text-sm font-medium mb-2">
                Сумма за контракт <span className="text-red-500">*</span>
              </label>
              <input
                type="number"
                value={price}
                onChange={(e) => setPrice(e.target.value)}
                className="input w-full"
                placeholder="Укажите стоимость этого контракта"
                min="1"
                required
              />
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                💡 Укажите сумму за этот контракт агитации
              </p>
            </div>
          )}
          <div>
            <label className="block text-sm font-medium mb-2">
              Категория <span className="text-red-500">*</span>
            </label>
            <select
              value={wnCategory}
              onChange={(e) => setWnCategory(e.target.value)}
              className="input w-full"
              required
            >
              <option value="Зеленка(чат)">Зеленка (чат)</option>
              <option value="Уведомление">Уведомление</option>
            </select>
          </div>
        </>
      )}

      {/* File Upload */}
      {contractType && contractType !== 'агитации-маркетплейс' && (
        <div>
          <label className="block text-sm font-medium mb-2">
            Скриншоты {contractType && <span className="text-red-500">*</span>}
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
              PNG, JPG, JPEG до 8MB
            </p>
          </div>

          {files.length > 0 && (
            <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4">
              {files.map((file, index) => (
                <div key={index} className="relative group">
                  <img
                    src={file.preview}
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
                  {contractType === 'товары' && (
                    <select
                      value={file.role || 'delivery'}
                      onChange={(e) => {
                        setFiles(prev => {
                          const updated = [...prev];
                          updated[index].role = e.target.value;
                          return updated;
                        });
                      }}
                      className="absolute bottom-2 left-2 right-2 text-xs input"
                    >
                      <option value="delivery">Сдача</option>
                      <option value="loading">Погрузка</option>
                    </select>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Submit Button */}
      <div className="flex gap-4">
        <button
          type="submit"
          disabled={loading || !contractType}
          className="btn btn-primary flex-1"
        >
          {loading ? 'Отправка...' : 'Отправить контракт'}
        </button>
      </div>
    </form>
  );
}

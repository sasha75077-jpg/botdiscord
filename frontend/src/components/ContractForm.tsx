import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { contractsApi, pricesApi } from '@/lib/api';
import { AlertCircle, CheckCircle, Upload, X } from 'lucide-react';

interface ContractFormProps {
  guildId: string;
  onSuccess?: () => void;
  restrictedToAgitation?: boolean; // true для recruiter
}

interface FileItem {
  file: File;
  preview: string;
  slot: string; // delivery | loading | main
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

const MAX_FILE = 8 * 1024 * 1024;

export default function ContractForm({ guildId, onSuccess, restrictedToAgitation = false }: ContractFormProps) {
  const [contractType, setContractType] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [files, setFiles] = useState<FileItem[]>([]);

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

  const { data: pricesData } = useQuery({
    queryKey: ['prices'],
    queryFn: async () => (await pricesApi.list()).data,
  });
  const priceMap: Record<string, number> = {};
  for (const p of (pricesData?.prices || []) as Array<{ item_key: string; price: number }>) {
    priceMap[p.item_key] = Number(p.price ?? 0);
  }
  const fmt = (n: number) => n.toLocaleString('ru-RU');

  const payoutHint = (): string | null => {
    switch (contractType) {
      case 'активация': {
        const n = Number(price);
        return n > 0 ? `Выплата: ${fmt(n)}` : null;
      }
      case 'тюнинг':
        return `Выплата: ${fmt(priceMap['tuning:with_screenshot'] || 0)}`;
      case 'ателье':
        return `Выплата за форму: ${fmt(priceMap['atelier.uniform'] || 0)}`;
      case 'агитации-маркетплейс':
        return `Выплата за ссылку: ${fmt(priceMap['agit:marketplace_link'] || 0)}`;
      case 'агитации-wn':
        return `Выплата: зеленка ${fmt(priceMap['agit:wn_green'] || 0)} / обзвон ${fmt(priceMap['agit:wn_notice'] || 0)}`;
      case 'металлургия-сдача': {
        const key: string | undefined = {
          'Железная руда': 'ore.delivery.iron', 'Серебряная руда': 'ore.delivery.silver',
          'Медная руда': 'ore.delivery.copper', 'Оловянная руда': 'ore.delivery.tin',
          'Золотая руда': 'ore.delivery.gold',
        }[oreType];
        return key ? `Выплата: ${fmt(priceMap[key] || 0)}` : null;
      }
      case 'товары':
        return `Доставка ${fmt(priceMap['goods.delivery'] || 0)} / погрузка ${fmt(priceMap['goods.loading'] || 0)}`;
      default:
        return null;
    }
  };

  const addFiles = (list: FileList | null, slot: string) => {
    if (!list) return;
    const items: FileItem[] = [];
    for (const f of Array.from(list)) {
      if (!f.type.startsWith('image/')) {
        setError(`Файл ${f.name} — не картинка`);
        continue;
      }
      if (f.size > MAX_FILE) {
        setError(`Файл ${f.name} больше 8 МБ`);
        continue;
      }
      items.push({ file: f, preview: URL.createObjectURL(f), slot });
    }
    setFiles((prev) => [...prev, ...items].slice(0, 10));
  };

  const removeFile = (index: number) => {
    setFiles((prev) => {
      const updated = [...prev];
      URL.revokeObjectURL(updated[index].preview);
      updated.splice(index, 1);
      return updated;
    });
  };

  const validate = (): { fields: Record<string, any>; price?: number } | string => {
    if (!contractType) return 'Выберите тип контракта';
    const fields: Record<string, any> = {};
    let priceNum: number | undefined;
    const n = files.length;

    switch (contractType) {
      case 'активация': {
        priceNum = Number(price);
        if (!priceNum || priceNum <= 0) return 'Укажите сумму (целое число > 0)';
        if (priceNum > 20000) return 'Сумма не должна превышать 20000';
        if (n !== 1) return 'Прикрепи 1 скриншот';
        fields.price = priceNum;
        break;
      }
      case 'дары-моря': {
        if (!fishType.trim()) return 'Укажите вид рыбы';
        const qty = Number(fishQty);
        if (!qty || qty <= 0) return 'Укажите количество (целое число > 0)';
        if (n < 1 || n > 10) return 'Нужно 1..10 скриншотов';
        fields.fishType = fishType.trim();
        fields.fishQty = qty;
        break;
      }
      case 'металлургия-сдача': {
        if (!oreType) return 'Выберите руду';
        if (n !== 1) return 'Прикрепи 1 скриншот';
        fields.oreType = oreType;
        break;
      }
      case 'металлургия-добыча': {
        fields.iron = Number(iron) || 0;
        fields.silver = Number(silver) || 0;
        fields.copper = Number(copper) || 0;
        fields.tin = Number(tin) || 0;
        fields.gold = Number(gold) || 0;
        if (!Object.values(fields).some((v) => (v as number) > 0)) {
          return 'Укажите количество хотя бы для одного ресурса';
        }
        if (n < 1 || n > 10) return 'Нужно 1..10 скриншотов';
        break;
      }
      case 'товары': {
        const hasDelivery = files.some((f) => f.slot === 'delivery');
        const hasLoading = files.some((f) => f.slot === 'loading');
        if (!hasDelivery && !hasLoading) return 'Прикрепи скрин погрузки или доставки';
        if (n > 2) return 'Максимум 2 скриншота';
        break;
      }
      case 'ателье': {
        const total = Number(totalUniforms);
        if (!total || total <= 0) return 'Укажите общее количество (целое число > 0)';
        if (n < 1 || n > 10) return 'Нужно 1..10 скриншотов';
        fields.totalUniforms = total;
        break;
      }
      case 'агитации-маркетплейс': {
        const validLinks = links.filter(l => l.trim());
        if (validLinks.length < 1) return 'Вставьте хотя бы 1 ссылку';
        fields.links = validLinks;
        if (restrictedToAgitation) {
          priceNum = Number(price);
          if (!priceNum || priceNum <= 0) return 'Укажите сумму за контракт';
          fields.price = priceNum;
        }
        if (n > 0) return 'Скриншоты не требуются';
        break;
      }
      case 'агитации-wn': {
        if (!wnCategory) return 'Выберите категорию';
        fields.wnCategory = wnCategory;
        if (restrictedToAgitation) {
          priceNum = Number(price);
          if (!priceNum || priceNum <= 0) return 'Укажите сумму за контракт';
          fields.price = priceNum;
        }
        if (n < 1 || n > 10) return 'Нужно 1..10 скриншотов';
        break;
      }
      case 'тюнинг': {
        if (n !== 1) return 'Прикрепи 1 скриншот';
        break;
      }
      default:
        return 'Неизвестный тип контракта';
    }
    return { fields, price: priceNum };
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess(false);

    const v = validate();
    if (typeof v === 'string') {
      setError(v);
      return;
    }
    setLoading(true);
    try {
      const form = new FormData();
      form.append('payload', JSON.stringify({
        contract_type: contractType,
        price: v.price,
        details: v.fields,
      }));
      files.forEach((f, i) => form.append(`file_${i}`, f.file, f.file.name));
      await contractsApi.createMultipart(guildId, form);
      setSuccess(true);
      files.forEach((f) => URL.revokeObjectURL(f.preview));
      setFiles([]);
      if (onSuccess) onSuccess();
    } catch (err: any) {
      setError(err.response?.data?.error || err.response?.data?.detail || 'Ошибка отправки');
    } finally {
      setLoading(false);
    }
  };

  const availableTypes = restrictedToAgitation
    ? CONTRACT_TYPES.filter(t => t.recruiterOnly)
    : CONTRACT_TYPES.filter(t => !t.recruiterOnly);

  const num = (label: string, value: string, set: (v: string) => void) => (
    <div>
      <label className="block text-sm font-medium mb-2">{label}</label>
      <input type="number" value={value} onChange={(e) => set(e.target.value)}
        className="input w-full" placeholder="0" min="0" />
    </div>
  );

  const fileBox = (slot: string, title: string) => {
    const onPaste = (e: React.ClipboardEvent) => {
      const items = e.clipboardData?.items;
      if (!items) return;
      const imgs: File[] = [];
      for (const it of Array.from(items)) {
        if (it.type.startsWith('image/')) {
          const f = it.getAsFile();
          if (f) imgs.push(f);
        }
      }
      if (imgs.length === 0) return;
      e.preventDefault();
      const mapped: FileItem[] = [];
      for (const f of imgs) {
        if (f.size > MAX_FILE) {
          setError(`Файл ${f.name} больше 8 МБ`);
          continue;
        }
        mapped.push({ file: f, preview: URL.createObjectURL(f), slot });
      }
      setFiles((prev) => [...prev, ...mapped].slice(0, 10));
    };
    return (
    <div
      onPaste={onPaste}
      className="border-2 border-dashed border-gray-300 dark:border-gray-700 rounded-lg p-4 text-center"
    >
      <p className="text-sm font-medium mb-2">{title}</p>
      <label className="cursor-pointer">
        <span className="text-primary-600 dark:text-primary-400 hover:underline text-sm">Выбрать файлы</span>
        <span className="text-gray-500 text-sm"> или вставь картинку из буфера (Ctrl+V)</span>
        <input type="file" accept="image/*" multiple onChange={(e) => addFiles(e.target.files, slot)} className="hidden" />
      </label>
      <div className="flex flex-wrap gap-2 justify-center mt-2">
        {files.map((f, i) => f.slot === slot && (
          <div key={i} className="relative">
            <img src={f.preview} alt="" className="w-20 h-20 object-cover rounded-lg" />
            <button type="button" onClick={() => removeFile(i)}
              className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full w-5 h-5 text-xs flex items-center justify-center">
              <X size={12} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {success && (
        <div className="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg flex items-center gap-3">
          <CheckCircle className="text-green-600 dark:text-green-400" size={20} />
          <p className="text-green-800 dark:text-green-200 font-medium">Контракт отправлен на проверку!</p>
        </div>
      )}
      {error && (
        <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-center gap-3">
          <AlertCircle className="text-red-600 dark:text-red-400" size={20} />
          <p className="text-red-800 dark:text-red-200">{error}</p>
        </div>
      )}

      <div>
        <label className="block text-sm font-medium mb-2">Тип контракта <span className="text-red-500">*</span></label>
        <select value={contractType} onChange={(e) => { setContractType(e.target.value); setFiles([]); }} className="input w-full" required>
          <option value="">— выбери тип —</option>
          {availableTypes.map((t) => (
            <option key={t.value} value={t.value}>{t.label}</option>
          ))}
        </select>
      </div>

      {(contractType === 'активация' || (restrictedToAgitation && contractType.startsWith('агитации'))) && (
        num('Сумма', price, setPrice)
      )}
      {contractType === 'дары-моря' && (
        <>
          <div>
            <label className="block text-sm font-medium mb-2">Вид рыбы</label>
            <input value={fishType} onChange={(e) => setFishType(e.target.value)} className="input w-full" placeholder="Например: золотая рыбка" />
          </div>
          {num('Количество', fishQty, setFishQty)}
        </>
      )}
      {contractType === 'металлургия-сдача' && (
        <div>
          <label className="block text-sm font-medium mb-2">Руда</label>
          <select value={oreType} onChange={(e) => setOreType(e.target.value)} className="input w-full">
            {['Железная руда', 'Серебряная руда', 'Медная руда', 'Оловянная руда', 'Золотая руда'].map((o) => (
              <option key={o} value={o}>{o}</option>
            ))}
          </select>
        </div>
      )}
      {contractType === 'металлургия-добыча' && (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {num('Железо', iron, setIron)}
          {num('Серебро', silver, setSilver)}
          {num('Медь', copper, setCopper)}
          {num('Олово', tin, setTin)}
          {num('Золото', gold, setGold)}
        </div>
      )}
      {contractType === 'ателье' && num('Общее количество формы', totalUniforms, setTotalUniforms)}
      {contractType === 'агитации-маркетплейс' && (
        <div>
          <label className="block text-sm font-medium mb-2">Ссылки (минимум 1)</label>
          {links.map((l, i) => (
            <div key={i} className="flex gap-2 mb-2">
              <input value={l} onChange={(e) => {
                const d = [...links];
                d[i] = e.target.value;
                setLinks(d);
              }} className="input flex-1" placeholder="https://..." />
              {links.length > 1 && (
                <button type="button" onClick={() => setLinks(links.filter((_, j) => j !== i))} className="btn btn-secondary px-3">✕</button>
              )}
            </div>
          ))}
          <button type="button" onClick={() => setLinks([...links, ''])} className="btn btn-secondary text-sm mt-1">+ ссылку</button>
        </div>
      )}
      {contractType === 'агитации-wn' && (
        <div>
          <label className="block text-sm font-medium mb-2">Категория</label>
          <input value={wnCategory} onChange={(e) => setWnCategory(e.target.value)} className="input w-full" placeholder="Категория" />
        </div>
      )}

      {contractType && contractType !== 'агитации-маркетплейс' && (
        <div className="space-y-3">
          <p className="text-sm font-medium flex items-center gap-2">
            <Upload size={16} /> Скриншоты <span className="text-red-500">*</span>
          </p>
          {contractType === 'товары' ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {fileBox('loading', 'Погрузка')}
              {fileBox('delivery', 'Доставка')}
            </div>
          ) : (
            fileBox('main', 'Прикрепи скриншоты')
          )}
          <p className="text-xs text-gray-500">До 8 МБ каждый. Улетят в Discord-канал, в базе только ссылки.</p>
        </div>
      )}

      {payoutHint() && (
        <div className="p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
          <p className="text-green-800 dark:text-green-200 font-semibold">💰 {payoutHint()}</p>
        </div>
      )}

      <button type="submit" disabled={loading} className="btn btn-primary w-full">
        {loading ? 'Отправка...' : 'Отправить контракт'}
      </button>
    </form>
  );
}

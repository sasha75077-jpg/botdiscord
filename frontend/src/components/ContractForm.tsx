import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAuthStore } from '@/store/authStore';
import { contractsApi, pricesApi } from '@/lib/api';
import { AlertCircle, CheckCircle } from 'lucide-react';

interface ContractFormProps {
  guildId: string;
  onSuccess?: () => void;
  restrictedToAgitation?: boolean; // true для recruiter
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
  const [contractType, setContractType] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

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
        return `Выплата за форму: ${fmt(priceMap['atelier:uniform'] ?? priceMap['atelier.uniform'] ?? 0)}`;
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
        return `Доставка ${fmt(priceMap['goods.delivery'] ?? priceMap['goods:delivery'] ?? 0)} / погрузка ${fmt(priceMap['goods.loading'] ?? priceMap['goods:loading'] ?? 0)}`;
      default:
        return null;
    }
  };

  const availableTypes = restrictedToAgitation
    ? CONTRACT_TYPES.filter(t => t.recruiterOnly)
    : CONTRACT_TYPES.filter(t => !t.recruiterOnly);

  const validate = (): { fields: Record<string, any>; price?: number } | string => {
    if (!contractType) return 'Выберите тип контракта';
    const fields: Record<string, any> = {};
    let priceNum: number | undefined;

    switch (contractType) {
      case 'активация': {
        priceNum = Number(price);
        if (!priceNum || priceNum <= 0) return 'Укажите сумму (целое число > 0)';
        if (priceNum > 20000) return 'Сумма не должна превышать 20000';
        fields.price = priceNum;
        break;
      }
      case 'дары-моря': {
        if (!fishType.trim()) return 'Укажите вид рыбы';
        const qty = Number(fishQty);
        if (!qty || qty <= 0) return 'Укажите количество (целое число > 0)';
        fields.fishType = fishType.trim();
        fields.fishQty = qty;
        break;
      }
      case 'металлургия-сдача': {
        if (!oreType) return 'Выберите руду';
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
        break;
      }
      case 'товары':
        break;
      case 'ателье': {
        const total = Number(totalUniforms);
        if (!total || total <= 0) return 'Укажите общее количество (целое число > 0)';
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
        break;
      }
      case 'тюнинг':
        break;
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
      await contractsApi.create(guildId, {
        contract_type: contractType,
        price: v.price,
        details: v.fields,
      });
      setSuccess(true);
      if (onSuccess) onSuccess();
    } catch (err: any) {
      setError(err.response?.data?.error || err.response?.data?.detail || 'Ошибка отправки');
    } finally {
      setLoading(false);
    }
  };

  const num = (label: string, value: string, set: (v: string) => void) => (
    <div>
      <label className="block text-sm font-medium mb-2">{label}</label>
      <input type="number" value={value} onChange={(e) => set(e.target.value)}
        className="input w-full" placeholder="0" min="0" />
    </div>
  );

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
        <select value={contractType} onChange={(e) => setContractType(e.target.value)} className="input w-full" required>
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

      <p className="text-sm text-gray-500">
        Скриншоты прикладывай в Discord-канале контрактов — на сайте пока только данные.
      </p>
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

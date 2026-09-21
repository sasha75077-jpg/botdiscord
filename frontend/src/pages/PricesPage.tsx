import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { pricesApi } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import { Banknote, Save, CheckCircle, AlertTriangle } from 'lucide-react';

const PRICE_LABELS: Record<string, string> = {
  'agit:wn_green': 'Агитации WN: зелёная',
  'agit:wn_notice': 'Агитации WN: объявление',
  'agit:marketplace_link': 'Агитации: маркетплейс',
  'atelier.uniform': 'Ателье: форма',
  'goods.delivery': 'Товары: доставка',
  'goods.loading': 'Товары: погрузка',
  'ore.delivery.copper': 'Руда: сдача Медь',
  'ore.delivery.gold': 'Руда: сдача Золото',
  'ore.delivery.iron': 'Руда: сдача Железо',
  'ore.delivery.silver': 'Руда: сдача Серебро',
  'ore.delivery.tin': 'Руда: сдача Олово',
  'tuning:with_screenshot': 'Тюнинг: со скриншотом',
  'courier:delivery': 'Курьер еды',
  'ore_unit:copper': 'Добыча руды: Медь',
  'ore_unit:gold': 'Добыча руды: Золото',
  'ore_unit:iron': 'Добыча руды: Железо',
  'ore_unit:silver': 'Добыча руды: Серебро',
  'ore_unit:tin': 'Добыча руды: Олово',
};

const CATEGORIES: Array<{ name: string; match: (k: string) => boolean }> = [
  { name: 'Агитации', match: (k) => k.startsWith('agit:') },
  { name: 'Товары', match: (k) => k.startsWith('goods.') },
  { name: 'Ателье', match: (k) => k.startsWith('atelier.') },
  { name: 'Тюнинг', match: (k) => k.startsWith('tuning:') },
  { name: 'Курьер', match: (k) => k.startsWith('courier:') },
  { name: 'Руда (сдача)', match: (k) => k.startsWith('ore.delivery.') },
  { name: 'Руда (добыча)', match: (k) => k.startsWith('ore_unit:') },
];

function labelOf(key: string): string {
  return PRICE_LABELS[key] || key;
}

export default function PricesPage() {
  const { user } = useAuthStore();
  const queryClient = useQueryClient();
  const canEdit = user?.role === 'owner' || user?.role === 'admin';
  const [draft, setDraft] = useState<Record<string, string> | null>(null);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['prices'],
    queryFn: async () => (await pricesApi.list()).data,
  });

  const items: Array<{ item_key: string; price: number }> = data?.prices || [];
  const shown: Record<string, string> = draft ?? Object.fromEntries(items.map((i) => [i.item_key, String(i.price ?? 0)]));
  const groups = CATEGORIES.map((c) => ({
    ...c,
    rows: items.filter((i) => c.match(i.item_key)),
  })).filter((g) => g.rows.length > 0);
  const other = items.filter((i) => !CATEGORIES.some((c) => c.match(i.item_key)));

  const save = useMutation({
    mutationFn: async () => {
      const parsed: Record<string, number> = {};
      for (const [k, v] of Object.entries(shown)) {
        const n = Number(String(v).replace(/\s/g, '').replace(',', '.'));
        if (!isFinite(n) || n < 0) throw new Error(`Плохая цена: ${k}`);
        parsed[k] = n;
      }
      await pricesApi.save(parsed);
    },
    onSuccess: () => {
      setDraft(null);
      setMsg({ ok: true, text: 'Сохранено, панель в Discord обновится за ~5 минут' });
      queryClient.invalidateQueries({ queryKey: ['prices'] });
    },
    onError: (e: any) => setMsg({ ok: false, text: e.message || e.response?.data?.error || 'Ошибка' }),
  });

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold flex items-center gap-2">
        <Banknote size={28} /> Выплаты
      </h1>

      {msg && (
        <div
          className={`p-3 rounded-lg border flex items-center gap-2 ${
            msg.ok
              ? 'bg-green-50 border-green-300 text-green-800 dark:bg-green-900/20 dark:border-green-800 dark:text-green-200'
              : 'bg-red-50 border-red-300 text-red-800 dark:bg-red-900/20 dark:border-red-800 dark:text-red-200'
          }`}
        >
          {msg.ok ? <CheckCircle size={18} /> : <AlertTriangle size={18} />}
          {msg.text}
        </div>
      )}

      {isLoading ? (
        <p className="text-gray-500">Загрузка...</p>
      ) : (
        <>
          {groups.map((g) => (
            <div className="card" key={g.name}>
              <h2 className="text-xl font-bold mb-3">{g.name}</h2>
              <div className="space-y-2">
                {g.rows.map((i) => (
                  <div key={i.item_key} className="flex items-center gap-3">
                    <p className="flex-1 text-sm truncate" title={i.item_key}>{labelOf(i.item_key)}</p>
                    {canEdit ? (
                      <input
                        type="number"
                        min="0"
                        value={shown[i.item_key] ?? ''}
                        onChange={(e) => setDraft({ ...shown, [i.item_key]: e.target.value })}
                        className="input w-36 text-right"
                      />
                    ) : (
                      <p className="font-bold w-36 text-right">
                        {Number(i.price ?? 0).toLocaleString('ru-RU')}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}
          {other.length > 0 && (
            <div className="card">
              <h2 className="text-xl font-bold mb-3">Прочее</h2>
              <div className="space-y-2">
                {other.map((i) => (
                  <div key={i.item_key} className="flex items-center gap-3">
                    <p className="flex-1 font-mono text-sm truncate" title={i.item_key}>{i.item_key}</p>
                    {canEdit ? (
                      <input
                        type="number"
                        min="0"
                        value={shown[i.item_key] ?? ''}
                        onChange={(e) => setDraft({ ...shown, [i.item_key]: e.target.value })}
                        className="input w-36 text-right"
                      />
                    ) : (
                      <p className="font-bold w-36 text-right">
                        {Number(i.price ?? 0).toLocaleString('ru-RU')}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
          {items.length === 0 && <p className="text-gray-500">Пусто.</p>}
          {canEdit && (
            <button
              onClick={() => save.mutate()}
              disabled={save.isPending || draft === null}
              className="btn btn-primary mt-4 flex items-center gap-2 disabled:opacity-40"
            >
              <Save size={18} /> Сохранить цены
            </button>
          )}
        </>
      )}
    </div>
  );
}

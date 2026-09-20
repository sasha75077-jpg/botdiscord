import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { pricesApi } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import { Banknote, Save, CheckCircle, AlertTriangle } from 'lucide-react';

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
        <div className="card">
          <div className="space-y-2">
            {items.map((i) => (
              <div key={i.item_key} className="flex items-center gap-3">
                <p className="flex-1 font-mono text-sm truncate">{i.item_key}</p>
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
            {items.length === 0 && <p className="text-gray-500">Пусто.</p>}
          </div>
          {canEdit && (
            <button
              onClick={() => save.mutate()}
              disabled={save.isPending || draft === null}
              className="btn btn-primary mt-4 flex items-center gap-2 disabled:opacity-40"
            >
              <Save size={18} /> Сохранить цены
            </button>
          )}
        </div>
      )}
    </div>
  );
}

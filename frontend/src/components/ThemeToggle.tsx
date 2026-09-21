import { useEffect, useState } from 'react';
import { Sun, Moon, Monitor } from 'lucide-react';

type Theme = 'auto' | 'dark' | 'light';

function applyTheme(t: Theme) {
  const dark = t === 'dark' || (t === 'auto' && window.matchMedia('(prefers-color-scheme: dark)').matches);
  document.documentElement.classList.toggle('dark', dark);
}

export function useTheme() {
  const [theme, setTheme] = useState<Theme>(() => {
    try {
      return (localStorage.getItem('theme') as Theme) || 'auto';
    } catch {
      return 'auto';
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem('theme', theme);
    } catch { /* ignore */ }
    applyTheme(theme);
    if (theme !== 'auto') return;
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const onChange = () => applyTheme('auto');
    mq.addEventListener('change', onChange);
    return () => mq.removeEventListener('change', onChange);
  }, [theme]);

  return { theme, setTheme };
}

export default function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const next: Theme = theme === 'auto' ? 'dark' : theme === 'dark' ? 'light' : 'auto';
  const Icon = theme === 'auto' ? Monitor : theme === 'dark' ? Moon : Sun;
  const title = theme === 'auto' ? 'Тема: как в системе' : theme === 'dark' ? 'Тема: тёмная' : 'Тема: светлая';
  return (
    <button
      onClick={() => setTheme(next)}
      title={`${title} (нажми чтобы сменить)`}
      className="p-2 rounded-lg text-gray-500 hover:text-gray-700 hover:bg-gray-100 dark:text-gray-400 dark:hover:text-gray-200 dark:hover:bg-dark-700 transition-colors"
    >
      <Icon size={20} />
    </button>
  );
}

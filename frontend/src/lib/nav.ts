// Полная перезагрузка страницы с сохранением базового пути и hash-маршрута.
// Нужен потому, что с HashRouter обычный window.location.href = '/login'
// уводит на корень домена (github.io/login) вместо /botdiscord/#/login.
export function href(path: string): string {
  const base = import.meta.env.BASE_URL || '/';
  const route = path.startsWith('/') ? path : `/${path}`;
  return `${base}#${route}`;
}

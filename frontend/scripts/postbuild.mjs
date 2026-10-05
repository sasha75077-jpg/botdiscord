import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

// Подставляет VITE_BASE_PATH в dist/404.html (public/ копируется как есть,
// поэтому Vite сам это сделать не может).
const here = path.dirname(fileURLToPath(import.meta.url));
const file = path.resolve(here, '..', 'dist', '404.html');

if (!existsSync(file)) {
  console.error('[postbuild] dist/404.html не найден');
  process.exit(1);
}

let base = process.env.VITE_BASE_PATH || '/';
if (!base.startsWith('/')) base = '/' + base;
if (!base.endsWith('/')) base += '/';

const html = readFileSync(file, 'utf8');
if (!html.includes('__BASE_PATH__')) {
  console.error('[postbuild] в 404.html нет плейсхолдера __BASE_PATH__');
  process.exit(1);
}

writeFileSync(file, html.split('__BASE_PATH__').join(base));
console.log(`[postbuild] 404.html: base = ${base}`);

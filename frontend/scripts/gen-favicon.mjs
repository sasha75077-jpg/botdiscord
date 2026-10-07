// Разовый генератор favicon.ico (32x32, PNG внутри ICO — так принимают все
// современные браузеры). Запуск: node scripts/gen-favicon.mjs
// Рисует скруглённый тёмный квадрат с буквой M в цвете акцента панели.
import zlib from 'node:zlib';
import fs from 'node:fs';

const S = 32;
const SS = 4; // суперсэмплинг 4x4 — сглаженные края
const BG = [17, 24, 39];    // #111827 — фон карточек
const FG = [56, 189, 248];  // #38bdf8 — акцент Melancholia
const R = 7 / S;            // радиус скругления

const inside = (x, y) => {
  const cx = Math.min(Math.max(x, R), 1 - R);
  const cy = Math.min(Math.max(y, R), 1 - R);
  const dx = x - cx;
  const dy = y - cy;
  return dx * dx + dy * dy <= R * R;
};

// Буква M: две вертикали + две диагонали, сходящиеся в центр
const T = 2.4; // толщина штриха, px
const letter = (x, y) => {
  if (y < 7 || y > 26) return false;
  if (Math.abs(x - 7.75) <= T) return true;
  if (Math.abs(x - 24.25) <= T) return true;
  if (y <= 21) {
    if (Math.abs(x - (7.75 + 0.714 * (y - 7))) <= T) return true;
    if (Math.abs(x - (24.25 - 0.714 * (y - 7))) <= T) return true;
  }
  return false;
};

// ---- PNG ----
const crcTable = Array.from({ length: 256 }, (_, n) => {
  let c = n;
  for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
  return c >>> 0;
});
const crc32 = (buf) => {
  let c = 0xffffffff;
  for (const b of buf) c = crcTable[(c ^ b) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
};
const chunk = (type, data) => {
  const len = Buffer.alloc(4);
  len.writeUInt32BE(data.length);
  const body = Buffer.concat([Buffer.from(type, 'ascii'), data]);
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(body));
  return Buffer.concat([len, body, crc]);
};

const raw = Buffer.alloc(S * (1 + S * 4));
for (let j = 0; j < S; j++) {
  const row = j * (1 + S * 4);
  raw[row] = 0; // filter: none
  for (let i = 0; i < S; i++) {
    let insideN = 0;
    let letterN = 0;
    for (let a = 0; a < SS; a++) {
      for (let b = 0; b < SS; b++) {
        const x = (i + (a + 0.5) / SS) / S;
        const y = (j + (b + 0.5) / SS) / S;
        if (!inside(x, y)) continue;
        insideN++;
        if (letter(i + (a + 0.5) / SS, j + (b + 0.5) / SS)) letterN++;
      }
    }
    const o = row + 1 + i * 4;
    const mix = insideN ? letterN / insideN : 0;
    raw[o] = Math.round(BG[0] + (FG[0] - BG[0]) * mix);
    raw[o + 1] = Math.round(BG[1] + (FG[1] - BG[1]) * mix);
    raw[o + 2] = Math.round(BG[2] + (FG[2] - BG[2]) * mix);
    raw[o + 3] = Math.round((insideN / (SS * SS)) * 255);
  }
}

const ihdr = Buffer.alloc(13);
ihdr.writeUInt32BE(S, 0);
ihdr.writeUInt32BE(S, 4);
ihdr[8] = 8;  // bit depth
ihdr[9] = 6;  // RGBA
const png = Buffer.concat([
  Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
  chunk('IHDR', ihdr),
  chunk('IDAT', zlib.deflateSync(raw, { level: 9 })),
  chunk('IEND', Buffer.alloc(0)),
]);

// ---- ICO (один образ 32x32 с данными PNG) ----
const header = Buffer.alloc(6);
header.writeUInt16LE(0, 0); // reserved
header.writeUInt16LE(1, 2); // type: icon
header.writeUInt16LE(1, 4); // count
const entry = Buffer.alloc(16);
entry[0] = S;               // width
entry[1] = S;               // height
entry[2] = 0;               // colors
entry[3] = 0;               // reserved
entry.writeUInt16LE(1, 4);  // planes
entry.writeUInt16LE(32, 6); // bpp
entry.writeUInt32LE(png.length, 8);
entry.writeUInt32LE(header.length + entry.length, 12); // offset

const ico = Buffer.concat([header, entry, png]);
fs.writeFileSync(new URL('../public/favicon.ico', import.meta.url), ico);
console.log(`favicon.ico: ${ico.length} bytes (PNG ${png.length} bytes)`);

// Превью в PNG (для проверки рисунка и как запасной <link rel="icon">)
const rows = [];
for (let j = 0; j < S; j++) rows.push(raw.subarray(j * (1 + S * 4), j * (1 + S * 4) + 1 + S * 4));
const png64 = (() => {
  const ih = Buffer.alloc(13);
  ih.writeUInt32BE(64, 0);
  ih.writeUInt32BE(64, 4);
  ih[8] = 8;
  ih[9] = 6;
  const big = Buffer.alloc(64 * (1 + 64 * 4));
  for (let j = 0; j < 64; j++) {
    for (let i = 0; i < 64; i++) {
      const sx = Math.min(S - 1, i >> 1);
      const sy = Math.min(S - 1, j >> 1);
      const src = sy * (1 + S * 4) + 1 + sx * 4;
      const dst = j * (1 + 64 * 4) + 1 + i * 4;
      big[dst] = raw[src];
      big[dst + 1] = raw[src + 1];
      big[dst + 2] = raw[src + 2];
      big[dst + 3] = raw[src + 3];
    }
  }
  return Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    chunk('IHDR', ih),
    chunk('IDAT', zlib.deflateSync(big, { level: 9 })),
    chunk('IEND', Buffer.alloc(0)),
  ]);
})();
fs.writeFileSync(new URL('../public/favicon.png', import.meta.url), png64);
console.log(`favicon.png: ${png64.length} bytes`);

export const DAY = 86_400_000;
export const HOUR = 3_600_000;

export const round = (n, d = 2) => (Number.isFinite(n) ? Math.round(n * 10 ** d) / 10 ** d : null);
export const lc = (s) => String(s ?? '').trim().toLowerCase();
export const pct = (num, den) => (den ? round((num / den) * 100) : null);
export const iso = (d) => (d ? new Date(d).toISOString() : '');
export const sum = (arr) => arr.reduce((a, b) => a + (Number(b) || 0), 0);

export function chunk(arr, n) {
  const out = [];
  for (let i = 0; i < arr.length; i += n) out.push(arr.slice(i, i + n));
  return out;
}

/** Local-time YYYY-MM-DD (respects the TZ env var). */
export function ymd(d) {
  const x = new Date(d);
  return `${x.getFullYear()}-${String(x.getMonth() + 1).padStart(2, '0')}-${String(x.getDate()).padStart(2, '0')}`;
}

/**
 * Parse the date formats these tools return:
 *  - epoch ms (Bamboo, Dynatrace)            1730000000000  (-1 = "not set" in Dynatrace)
 *  - ISO with +0800 offset (Jira, Sonar)      2026-08-03T10:00:00.000+0800
 *  - ServiceNow UTC                           2026-08-03 02:00:00
 *  - plain ISO / date-only                    2026-08-03
 */
export function parseDate(v) {
  if (v === null || v === undefined || v === '' || v === -1) return null;
  if (typeof v === 'number') return new Date(v);
  let s = String(v).trim();
  if (/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(s)) s = s.replace(' ', 'T') + 'Z';
  s = s.replace(/T(.*)([+-]\d{2})(\d{2})$/, 'T$1$2:$3');
  const d = new Date(s);
  return Number.isNaN(d.getTime()) ? null : d;
}

export function percentile(sorted, p) {
  if (!sorted.length) return null;
  const idx = (p / 100) * (sorted.length - 1);
  const lo = Math.floor(idx);
  const hi = Math.ceil(idx);
  return sorted[lo] + (sorted[hi] - sorted[lo]) * (idx - lo);
}

/** count / mean / median / p85 / min / max for a list of numbers. */
export function summarize(values) {
  const v = values.filter(Number.isFinite).sort((a, b) => a - b);
  if (!v.length) return { count: 0, mean: null, median: null, p85: null, min: null, max: null };
  return {
    count: v.length,
    mean: round(sum(v) / v.length),
    median: round(percentile(v, 50)),
    p85: round(percentile(v, 85)),
    min: round(v[0]),
    max: round(v[v.length - 1]),
  };
}

/** CSV with every string, date and object quoted (numbers/booleans stay bare) so spreadsheets don't reinterpret keys or dates. */
export function toCsv(rows) {
  if (!rows?.length) return '';
  const cols = [...new Set(rows.flatMap((r) => Object.keys(r)))];
  const quote = (s) => `"${s.replace(/"/g, '""')}"`;
  const esc = (v) => {
    if (v === null || v === undefined) return '';
    if (typeof v === 'number' || typeof v === 'boolean' || typeof v === 'bigint') return String(v);
    return quote(v instanceof Date ? v.toISOString() : typeof v === 'object' ? JSON.stringify(v) : String(v));
  };
  return [cols.map(quote).join(','), ...rows.map((r) => cols.map((c) => esc(r[c])).join(','))].join('\n') + '\n';
}

export function htmlToText(html) {
  return String(html ?? '')
    .replace(/<(script|style)[\s\S]*?<\/\1>/gi, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/\s+/g, ' ')
    .trim();
}

/**
 * Text similarity 0..1 (Sørensen–Dice on word bigrams). 1 = identical wording.
 * Used to estimate "accepted with minimal rework" for Gen-e2 drafts.
 */
export function similarity(a, b) {
  const words = (s) => lc(s).replace(/[^\p{L}\p{N}\s]+/gu, ' ').split(/\s+/).filter(Boolean);
  const grams = (w) => {
    const items = w.length < 2 ? w : w.slice(1).map((x, i) => `${w[i]} ${x}`);
    const m = new Map();
    for (const g of items) m.set(g, (m.get(g) ?? 0) + 1);
    return [m, items.length];
  };
  const [ma, na] = grams(words(a));
  const [mb, nb] = grams(words(b));
  if (!na && !nb) return 1;
  if (!na || !nb) return 0;
  let inter = 0;
  for (const [g, c] of ma) inter += Math.min(c, mb.get(g) ?? 0);
  return (2 * inter) / (na + nb);
}

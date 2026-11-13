import { DAY, ymd } from './util.js';

/** Read an env var; empty strings count as unset. */
export function env(key, def) {
  const v = process.env[key];
  return v === undefined || v.trim() === '' ? def : v.trim();
}

/** Comma-separated list env var. */
export function list(key, def = []) {
  const v = env(key);
  return v ? v.split(',').map((s) => s.trim()).filter(Boolean) : def;
}

export function bool(key, def = false) {
  const v = env(key);
  return v === undefined ? def : /^(1|true|yes|y|on)$/i.test(v);
}

export function num(key, def) {
  const v = env(key);
  if (v === undefined) return def;
  const n = Number(v);
  if (!Number.isFinite(n)) throw new Error(`${key} must be a number (got "${v}")`);
  return n;
}

/** Return the required keys that are unset. "A|B" means either A or B satisfies the requirement. */
export function missingEnv(required) {
  return required.filter((k) => !k.split('|').some((alt) => env(alt)));
}

const LEVELS = { error: 0, warn: 1, info: 2, debug: 3 };
const level = () => LEVELS[(env('LOG_LEVEL', 'info') || 'info').toLowerCase()] ?? 2;
export const log = {
  error: (...a) => level() >= 0 && console.error('[error]', ...a),
  warn: (...a) => level() >= 1 && console.error('[warn] ', ...a),
  info: (...a) => level() >= 2 && console.error('[info] ', ...a),
  debug: (...a) => level() >= 3 && console.error('[debug]', ...a),
};

/**
 * Reporting window. Dates are interpreted in the process time zone (set TZ, e.g. TZ=Asia/Singapore).
 * Defaults to the 90 days ending yesterday.
 */
export function reportRange() {
  const re = /^\d{4}-\d{2}-\d{2}$/;
  const toStr = env('REPORT_TO') ?? ymd(Date.now() - DAY);
  const fromStr = env('REPORT_FROM') ?? ymd(new Date(`${toStr}T00:00:00`).getTime() - 89 * DAY);
  if (!re.test(fromStr) || !re.test(toStr)) throw new Error('REPORT_FROM / REPORT_TO must be YYYY-MM-DD');
  const from = new Date(`${fromStr}T00:00:00`);
  const to = new Date(`${toStr}T23:59:59.999`);
  if (to < from) throw new Error('REPORT_TO is before REPORT_FROM');
  return { fromStr, toStr, toExclusiveStr: ymd(to.getTime() + 1), from, to };
}

import { setTimeout as sleep } from 'node:timers/promises';
import { env, num, log } from './config.js';
import { dry, dryAllowed, DryRunBlocked } from './dryrun.js';

export const basicAuth = (user, pass) => `Basic ${Buffer.from(`${user ?? ''}:${pass ?? ''}`).toString('base64')}`;

export class HttpError extends Error {
  constructor(message, status, body) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

/** Set by configureProxy(): { fetch, dispatcher } when a proxy is in use. */
let proxied;

async function backoff(attempt, retryAfter) {
  const ra = Number(retryAfter);
  const ms = Number.isFinite(ra) && ra > 0 ? ra * 1000 : Math.min(30_000, 1000 * 2 ** attempt) + Math.random() * 250;
  log.debug(`retrying in ${Math.round(ms)}ms`);
  await sleep(ms);
}

/** fetch wrapper: JSON in/out, retries on network errors, 429 and 5xx (honours Retry-After). */
export async function request(url, { method = 'GET', headers = {}, body } = {}) {
  if (dry.on && !dryAllowed(url)) throw new DryRunBlocked(url);
  const retries = num('HTTP_RETRIES', 4);
  const timeout = num('HTTP_TIMEOUT_MS', 60_000);
  for (let attempt = 0; ; attempt++) {
    let res;
    try {
      log.debug(`${method} ${url}`);
      res = await (proxied?.fetch ?? fetch)(url, {
        ...(proxied && { dispatcher: proxied.dispatcher }),
        method,
        headers: {
          Accept: 'application/json',
          ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
          ...headers,
        },
        body: body === undefined ? undefined : JSON.stringify(body),
        signal: AbortSignal.timeout(timeout),
      });
    } catch (err) {
      if (attempt < retries) {
        await backoff(attempt);
        continue;
      }
      throw new Error(`${method} ${url} failed: ${err.cause?.message ?? err.message}`);
    }
    if ((res.status === 429 || res.status >= 500) && attempt < retries) {
      await backoff(attempt, res.headers.get('retry-after'));
      continue;
    }
    const text = await res.text();
    if (!res.ok) throw new HttpError(`${method} ${url} -> HTTP ${res.status}: ${text.slice(0, 400)}`, res.status, text);
    if (!text) return null;
    try {
      return JSON.parse(text);
    } catch {
      return text;
    }
  }
}

/** Small REST client bound to a base URL and default headers. Query values may be arrays (repeated params). */
export function createClient(baseUrl, headers = {}) {
  if (!baseUrl) throw new Error('createClient: base URL is not set');
  const base = baseUrl.replace(/\/+$/, '');
  const build = (path, query) => {
    const url = new URL(/^https?:\/\//.test(path) ? path : base + (path.startsWith('/') ? path : `/${path}`));
    for (const [k, v] of Object.entries(query ?? {})) {
      if (v === undefined || v === null || v === '') continue;
      for (const item of Array.isArray(v) ? v : [v]) url.searchParams.append(k, String(item));
    }
    return url.toString();
  };
  return {
    get: (path, query, extra) => request(build(path, query), { headers: { ...headers, ...extra } }),
    post: (path, body, query, extra) => request(build(path, query), { method: 'POST', body, headers: { ...headers, ...extra } }),
  };
}

/** Like createClient, but the base URL is resolved asynchronously on first use (cached). */
export function createLazyClient(resolveBase, headers = {}) {
  let inner;
  const get = () => (inner ??= resolveBase().then((base) => createClient(base, headers)));
  return {
    get: async (...a) => (await get()).get(...a),
    post: async (...a) => (await get()).post(...a),
  };
}

/** Promise.all with a concurrency limit. */
export async function pMap(items, fn, limit = num('HTTP_CONCURRENCY', 5)) {
  const results = new Array(items.length);
  let i = 0;
  const workers = Array.from({ length: Math.max(1, Math.min(limit, items.length)) }, async () => {
    while (i < items.length) {
      const idx = i++;
      results[idx] = await fn(items[idx], idx);
    }
  });
  await Promise.all(workers);
  return results;
}

/**
 * Route requests through HTTPS_PROXY / HTTP_PROXY (respecting NO_PROXY) if set.
 *
 * Uses undici's own fetch with an explicit dispatcher. Installing a dispatcher from the npm undici package
 * into Node's built-in fetch is unreliable: when the two undici versions differ, the proxy is silently
 * bypassed (or requests hang). Fails loudly instead of silently connecting direct.
 */
export async function configureProxy() {
  if (!(env('HTTPS_PROXY') || env('https_proxy') || env('HTTP_PROXY') || env('http_proxy'))) return;
  let undici;
  try {
    undici = await import('undici');
  } catch {
    throw new Error('HTTPS_PROXY/HTTP_PROXY is set but the "undici" package is not installed, so the proxy cannot be used. Run: npm install');
  }
  proxied = { fetch: undici.fetch, dispatcher: new undici.EnvHttpProxyAgent() };
  log.info(`Using proxy from environment (HTTPS_PROXY=${env('HTTPS_PROXY', env('https_proxy', '-')).replace(/\/\/[^@/]*@/, '//***@')}, NO_PROXY=${env('NO_PROXY', env('no_proxy', '-'))})`);
}

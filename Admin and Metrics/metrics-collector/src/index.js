#!/usr/bin/env node
// Engineering metrics collector - configured entirely through environment variables.
//   node src/index.js            run METRICS (default: all whose config is present)
//   node src/index.js --list     list metrics and required env vars
//   node src/index.js --check    show which metrics are runnable with the current env
//   node src/index.js --dry-run  show how many Jira issues each runnable metric would fetch (counts only)
//   node src/index.js --selftest test connectivity/auth to each configured tool (read-only)
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';

try {
  (await import('dotenv')).config({ path: process.env.ENV_FILE || '.env', quiet: true });
} catch {
  /* dotenv optional */
}

const { env, list, missingEnv, reportRange, log } = await import('./lib/config.js');
const { configureProxy } = await import('./lib/http.js');
const { toCsv } = await import('./lib/util.js');
const registry = [
  ...(await import('./metrics/delivery.js')).default,
  ...(await import('./metrics/security-stability.js')).default,
  ...(await import('./metrics/requirements.js')).default,
];

const requiresOf = (m) => (typeof m.requires === 'function' ? m.requires() : m.requires);
const args = new Set(process.argv.slice(2));

if (args.has('--list') || args.has('--check')) {
  const rows = registry.map((m) => {
    const miss = missingEnv(requiresOf(m));
    return { metric: m.key, category: m.category, source: m.source, ready: miss.length ? 'no' : 'yes', [args.has('--check') ? 'missing' : 'requires']: (args.has('--check') ? miss : requiresOf(m)).join(' ') };
  });
  console.table(rows);
  process.exit(0);
}

await configureProxy();
if (args.has('--selftest')) {
  const { selftest } = await import('./selftest.js');
  process.exit(await selftest());
}
const range = reportRange();
const wanted = list('METRICS', ['all']).map((s) => s.toLowerCase());
const unknown = wanted.filter((k) => k !== 'all' && !registry.some((m) => m.key === k));
if (unknown.length) {
  log.error(`Unknown metric(s): ${unknown.join(', ')}. Use --list to see available keys.`);
  process.exit(2);
}
const selected = registry.filter((m) => wanted.includes('all') || wanted.includes(m.key));
const explicit = !wanted.includes('all');

log.info(`Report window ${range.fromStr} -> ${range.toStr} (TZ=${Intl.DateTimeFormat().resolvedOptions().timeZone})`);
const runId = new Date().toISOString().replace(/[:.]/g, '-');
const outDir = path.resolve(env('OUTPUT_DIR', 'output'), runId);
await mkdir(outDir, { recursive: true });

if (args.has('--dry-run')) {
  const { dryRun } = await import('./dryrun-report.js');
  await dryRun(selected, range, requiresOf, explicit);
  process.exit(0);
}

const results = [];
for (const m of selected) {
  const base = { key: m.key, name: m.name, category: m.category, source: m.source };
  const missing = missingEnv(requiresOf(m));
  if (missing.length) {
    (explicit ? log.warn : log.debug)(`${m.key}: skipped, missing ${missing.join(', ')}`);
    results.push({ ...base, status: 'skipped', missing });
    continue;
  }
  log.info(`${m.key}: running...`);
  const t0 = Date.now();
  try {
    const r = await m.run({ range });
    const { details = [], ...rest } = r;
    if (details.length) await writeFile(path.join(outDir, `${m.key}.csv`), toCsv(details));
    results.push({ ...base, status: 'ok', ...rest, detailRows: details.length, durationMs: Date.now() - t0 });
    log.info(`${m.key}: ${r.value ?? 'n/a'} ${r.unit ?? ''} (${details.length} rows, ${Date.now() - t0}ms)`);
  } catch (e) {
    log.error(`${m.key}: ${e.message}`);
    if (env('LOG_LEVEL') === 'debug') console.error(e.stack);
    results.push({ ...base, status: 'error', error: e.message, durationMs: Date.now() - t0 });
  }
}

const report = { generatedAt: new Date().toISOString(), window: { from: range.fromStr, to: range.toStr }, metrics: results };
await writeFile(path.join(outDir, 'summary.json'), JSON.stringify(report, null, 2));
await writeFile(
  path.join(outDir, 'summary.csv'),
  toCsv(results.map((r) => ({ category: r.category, metric: r.name, key: r.key, status: r.status, value: r.value, unit: r.unit, detail: r.error ?? (r.missing ? `missing: ${r.missing.join(' ')}` : JSON.stringify(r.summary ?? {})) }))),
);

console.table(results.map((r) => ({ metric: r.key, status: r.status, value: r.value ?? '', unit: r.unit ?? (r.missing ? `missing ${r.missing.join(' ')}` : r.error ?? '') })));
log.info(`Output written to ${outDir}`);
process.exitCode = results.some((r) => r.status === 'error') ? 1 : 0;

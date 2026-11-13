import { log, num } from './config.js';

/**
 * Throttled progress logger for long loops. Logs at most every PROGRESS_INTERVAL_MS (default 5000) at info level,
 * plus a final line if anything was logged before (so short jobs stay silent).
 *   const tick = progress('Jira changelogs', ids.length);  // known total
 *   const tick = progress('Jira search');                  // unknown total: logs a running count
 *   tick(n);                                               // n items done (default 1)
 */
export function progress(label, total) {
  const every = num('PROGRESS_INTERVAL_MS', 5000);
  const t0 = Date.now();
  let done = 0;
  let last = t0;
  let logged = false;
  const line = () => {
    const secs = ((Date.now() - t0) / 1000).toFixed(0);
    const of = total === undefined ? '' : `/${total} (${Math.round((done / Math.max(total, 1)) * 100)}%)`;
    log.info(`${label}: ${done}${of} [${secs}s]`);
    logged = true;
    last = Date.now();
  };
  return (n = 1) => {
    done += n;
    if (total !== undefined && done >= total) {
      if (logged || every === 0) line();
    } else if (Date.now() - last >= every) line();
  };
}

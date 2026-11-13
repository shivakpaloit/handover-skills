// `--dry-run`: show how much Jira data each runnable metric would fetch, using count-only calls.
import { env, missingEnv, log, num } from './lib/config.js';
import { dry, DryRunBlocked } from './lib/dryrun.js';

// Extra per-issue work a metric does after searching (beyond the search pages themselves).
const EXTRA = {
  cycle_time: (n) => ({ calls: Math.ceil(n / 1000), what: 'bulk changelog calls' }),
  gene2_acceptance_rate: (n) => ({ calls: Math.ceil(n / 1000), what: 'bulk changelog calls (plus up to two attachment/page downloads per PRD)' }),
  prd_to_story_lead_time: (n) =>
    env('PRD_SOURCE') === 'epic' || (!env('PRD_SOURCE') && !env('CONFLUENCE_PRD_CQL') && !env('JPD_IDEAS_JQL'))
      ? { calls: Math.ceil(n / 100), what: 'child-story queries (100 epics each; epic mode, not estimated here because epics are only counted)' }
      : { calls: n, what: 'remote-link calls, one per story (Confluence mode)' },
};

export async function dryRun(selected, range, requiresOf, explicit) {
  console.error(`Dry run for ${range.fromStr} -> ${range.toStr}: counts only, nothing is fetched or written. Counts are approximate.`);
  const rows = [];
  const notes = [];
  let totalIssues = 0;
  let totalCalls = 0;

  for (const m of selected) {
    const missing = missingEnv(requiresOf(m));
    if (missing.length) {
      if (explicit) notes.push(`${m.key}: skipped, missing ${missing.join(' ')}`);
      continue;
    }
    dry.on = true;
    dry.current = m.key;
    const before = dry.searches.length;
    let blocked = false;
    try {
      await m.run({ range });
    } catch (e) {
      if (e instanceof DryRunBlocked) {
        blocked = true;
        notes.push(`${m.key}: not estimated beyond this point, it next calls ${e.where}`);
      } else notes.push(`${m.key}: ${e.message.split('\n')[0].slice(0, 160)}`);
    } finally {
      dry.on = false;
    }
    const mine = dry.searches.slice(before);
    let issues = 0;
    let calls = 0;
    for (const s of mine) {
      issues += s.count;
      calls += Math.ceil(s.count / (s.fields <= 1 ? 1000 : 100));
      rows.push({ metric: m.key, query: s.jql.length > 90 ? `${s.jql.slice(0, 87)}...` : s.jql, issues: s.count, 'search calls': Math.ceil(s.count / (s.fields <= 1 ? 1000 : 100)) });
    }
    const extra = blocked ? undefined : EXTRA[m.key]?.(issues);
    if (extra) {
      calls += extra.calls;
      notes.push(`${m.key}: + ~${extra.calls} ${extra.what}`);
    }
    if (!mine.length && !notes.some((n) => n.startsWith(`${m.key}:`))) notes.push(`${m.key}: no Jira issue searches`);
    totalIssues += issues;
    totalCalls += calls;
  }

  if (rows.length) console.table(rows);
  for (const n of notes) console.error(`  ${n}`);
  const conc = num('HTTP_CONCURRENCY', 5);
  console.error(`Total: ~${totalIssues} issues to fetch across ${rows.length} queries, ~${totalCalls} API calls (HTTP_CONCURRENCY=${conc}).`);
  log.info('To narrow: tighten JIRA_SCOPE_JQL / REPORT_FROM / REPORT_TO, or run one metric with METRICS=<key>.');
}

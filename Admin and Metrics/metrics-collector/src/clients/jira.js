// Jira Cloud REST v3 (also used for Jira Product Discovery, which stores ideas as Jira issues).
import { env, bool, log } from '../lib/config.js';
import { createLazyClient, basicAuth, pMap } from '../lib/http.js';
import { jiraBase } from '../lib/atlassian.js';
import { chunk, lc, parseDate } from '../lib/util.js';
import { progress } from '../lib/progress.js';
import { dry, noteSearch } from '../lib/dryrun.js';

let _c;
const client = () =>
  (_c ??= createLazyClient(jiraBase, { Authorization: basicAuth(env('JIRA_EMAIL'), env('JIRA_API_TOKEN')) }));

export const REQUIRED = ['JIRA_BASE_URL', 'JIRA_EMAIL', 'JIRA_API_TOKEN'];

/** Quote values for a JQL list: ["In Progress","Done"] -> "In Progress", "Done" */
export const jqlList = (values) => values.map((v) => `"${String(v).replace(/"/g, '\\"')}"`).join(', ');

/** AND together JIRA_SCOPE_JQL (if set) and any extra clauses, each wrapped in parentheses. */
export const scoped = (...clauses) => [env('JIRA_SCOPE_JQL'), ...clauses].filter(Boolean).map((c) => `(${c})`).join(' AND ');
export const and = (...clauses) => clauses.filter(Boolean).map((c) => `(${c})`).join(' AND ');

/** Enhanced JQL search (POST /rest/api/3/search/jql) with nextPageToken paging. */
export async function searchIssues(jql, fields = ['key']) {
  log.debug(`JQL: ${jql}`);
  if (dry.on) {
    noteSearch(jql, await approximateCount(jql), fields);
    return [];
  }
  const out = [];
  const tick = progress('Jira search (issues fetched)');
  const maxResults = fields.length <= 1 ? 1000 : 100;
  let nextPageToken;
  do {
    const r = await client().post('/rest/api/3/search/jql', { jql, fields, maxResults, ...(nextPageToken && { nextPageToken }) });
    out.push(...(r?.issues ?? []));
    tick(r?.issues?.length ?? 0);
    nextPageToken = r?.isLast === false || (r?.nextPageToken && r?.isLast !== true) ? r.nextPageToken : undefined;
  } while (nextPageToken);
  return out;
}

/** Cheap approximate match count (POST /rest/api/3/search/approximate-count). */
export async function approximateCount(jql) {
  const r = await client().post('/rest/api/3/search/approximate-count', { jql });
  return r?.count ?? 0;
}

/**
 * Number of issues matching a JQL. Uses Jira's approximate-count (one cheap call, can be slightly off on very large
 * result sets); set JIRA_EXACT_COUNTS=true, or fall back automatically if the endpoint is unavailable, to count by paging keys.
 */
export async function countIssues(jql) {
  if (!bool('JIRA_EXACT_COUNTS')) {
    try {
      return await approximateCount(jql);
    } catch (e) {
      if (![400, 403, 404, 405].includes(e.status)) throw e;
      log.warn(`approximate-count unavailable (HTTP ${e.status}); counting by paging keys instead`);
    }
  }
  return (await searchIssues(jql, ['key'])).length;
}

/** Fetch issues by key/id, silently dropping keys that don't exist (POST /rest/api/3/issue/bulkfetch). */
export async function bulkFetch(keys, fields) {
  const out = [];
  const unique = [...new Set(keys)];
  const tick = progress('Jira issue bulk fetch', unique.length);
  for (const batch of chunk(unique, 100)) {
    const r = await client().post('/rest/api/3/issue/bulkfetch', { issueIdsOrKeys: batch, fields });
    out.push(...(r?.issues ?? []));
    tick(batch.length);
  }
  return out;
}

/**
 * Changelogs for many issues, filtered to the given fields. Returns Map(issueId -> changeHistories[]).
 * Uses the bulk changelog endpoint; falls back to per-issue paging if unavailable.
 */
export async function changelogs(issueIds, fieldIds = ['status']) {
  const ids = [...new Set(issueIds.map(String))];
  const map = new Map(ids.map((id) => [id, []]));
  if (!ids.length) return map;
  const tick = progress('Jira changelogs', ids.length);
  try {
    for (const batch of chunk(ids, 1000)) {
      let nextPageToken;
      do {
        const r = await client().post('/rest/api/3/changelog/bulkfetch', {
          issueIdsOrKeys: batch,
          fieldIds,
          maxResults: 1000,
          ...(nextPageToken && { nextPageToken }),
        });
        for (const l of r?.issueChangeLogs ?? []) map.get(String(l.issueId))?.push(...(l.changeHistories ?? []));
        nextPageToken = r?.nextPageToken;
      } while (nextPageToken);
      tick(batch.length);
    }
  } catch (e) {
    if (![400, 404, 405].includes(e.status)) throw e;
    log.warn(`Bulk changelog unavailable (HTTP ${e.status}); falling back to per-issue changelog calls`);
    const tick2 = progress('Jira changelogs (per issue)', ids.length);
    await pMap(ids, async (id) => {
      const vals = [];
      for (let startAt = 0; ; ) {
        const r = await client().get(`/rest/api/3/issue/${id}/changelog`, { startAt, maxResults: 100 });
        vals.push(...(r?.values ?? []));
        if (r?.isLast || !r?.values?.length) break;
        startAt += r.values.length;
      }
      map.set(id, vals);
      tick2();
    });
  }
  return map;
}

/** Flatten histories into sorted [{at, from, to}] for one field. */
export function transitions(histories = [], fieldId = 'status') {
  const out = [];
  for (const h of histories)
    for (const it of h.items ?? [])
      if ((it.fieldId ?? it.field) === fieldId || lc(it.field) === lc(fieldId))
        out.push({ at: parseDate(h.created), from: it.fromString, to: it.toString });
  return out.sort((a, b) => a.at - b.at);
}

/**
 * Resolve a point in time per issue. spec:
 *   "created"                 -> issue created date (issues must include the `created` field)
 *   "status:Approved|Ready"   -> first transition into any of those statuses
 * Returns Map(issueKey -> Date|null).
 */
export async function eventTimes(issues, spec = 'created') {
  const out = new Map();
  if (!spec || lc(spec) === 'created') {
    for (const i of issues) out.set(i.key, parseDate(i.fields?.created));
    return out;
  }
  const m = /^status:(.+)$/i.exec(spec);
  if (!m) throw new Error(`Unsupported time spec "${spec}" (use "created" or "status:Name|Other Name")`);
  const wanted = new Set(m[1].split('|').map(lc));
  const logs = await changelogs(issues.map((i) => i.id), ['status']);
  for (const i of issues) {
    const t = transitions(logs.get(String(i.id)), 'status').find((x) => wanted.has(lc(x.to)));
    out.set(i.key, t?.at ?? null);
  }
  return out;
}

/** Raw text of an attachment (needs read:attachment:jira for scoped tokens). */
export const attachmentText = (id) => client().get(`/rest/api/3/attachment/content/${id}`);

export const remoteLinks = (key) => client().get(`/rest/api/3/issue/${key}/remotelink`);

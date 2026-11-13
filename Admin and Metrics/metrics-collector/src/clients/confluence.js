// Confluence Cloud (same Atlassian site + credentials as Jira).
import { env } from '../lib/config.js';
import { createLazyClient, basicAuth } from '../lib/http.js';
import { confluenceBase } from '../lib/atlassian.js';

let _c;
const client = () =>
  (_c ??= createLazyClient(confluenceBase, {
    Authorization: basicAuth(env('JIRA_EMAIL'), env('JIRA_API_TOKEN')),
  }));

export const REQUIRED = ['JIRA_BASE_URL|CONFLUENCE_BASE_URL', 'JIRA_EMAIL', 'JIRA_API_TOKEN'];

/** Count content matching CQL. */
export async function cqlCount(cql) {
  const r = await client().get('/rest/api/search', { cql, limit: 1 });
  return r?.totalSize ?? r?.size ?? 0;
}

/** All content matching CQL (follows _links.next cursors). Each result includes history.createdDate. */
export async function cqlPages(cql, expand = 'history') {
  const out = [];
  let r = await client().get('/rest/api/content/search', { cql, limit: 100, expand });
  for (;;) {
    out.push(...(r?.results ?? []));
    const next = r?._links?.next;
    if (!next) break;
    r = await client().get(next.replace(/^\/wiki(?=\/)/, '')); // next is relative to the /wiki context
  }
  return out;
}

/** Page body (storage format). version omitted = current. */
export async function pageBody(id, version) {
  const r = await client().get(`/api/v2/pages/${id}`, { 'body-format': 'storage', version });
  return { body: r?.body?.storage?.value ?? '', version: r?.version?.number };
}

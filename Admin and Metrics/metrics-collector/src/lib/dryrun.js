// Dry-run support (`--dry-run`): metrics run against a recording Jira client that only issues cheap count calls.
// Anything else (other tools, bulk fetches, changelogs) is blocked and reported instead of executed.
export const dry = { on: false, current: null, searches: [] };

export class DryRunBlocked extends Error {
  constructor(url) {
    const u = new URL(url);
    super(`dry-run: would call ${u.host}`);
    this.host = u.host;
    this.where = `${u.host}${u.pathname.replace(/\/ex\/(jira|confluence)\/[0-9a-f-]+/, '/ex/$1/<cloudId>')}`;
  }
}

/** Requests that are cheap and read-only enough to allow in a dry run. */
export const dryAllowed = (url) => /\/search\/approximate-count|\/_edge\/tenant_info|\/wiki\/rest\/api\/search\?|\/rest\/api\/search\?/.test(url);

export const noteSearch = (jql, count, fields) => dry.searches.push({ metric: dry.current, jql, count, fields: fields.length });

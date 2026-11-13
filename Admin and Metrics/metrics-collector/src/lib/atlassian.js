// Base URLs for Jira / Confluence Cloud.
//   ATLASSIAN_TOKEN_TYPE=scoped (default): scoped API tokens only work through the API gateway,
//     https://api.atlassian.com/ex/{jira|confluence}/<cloudId>/..., authenticated with the same
//     email + token as basic auth. The cloud ID comes from ATLASSIAN_CLOUD_ID, or is looked up
//     from https://<site>/_edge/tenant_info (public, no auth).
//   ATLASSIAN_TOKEN_TYPE=classic: calls go to the site URL (JIRA_BASE_URL).
import { env } from './config.js';
import { request } from './http.js';

const tokenType = () => (env('ATLASSIAN_TOKEN_TYPE', 'scoped')).toLowerCase();
const strip = (u) => u.replace(/\/+$/, '');

let cloudIdPromise;
function cloudId() {
  return (cloudIdPromise ??= (async () => {
    if (env('ATLASSIAN_CLOUD_ID')) return env('ATLASSIAN_CLOUD_ID');
    const site = env('JIRA_BASE_URL') ?? env('CONFLUENCE_BASE_URL');
    if (!site) throw new Error('Set JIRA_BASE_URL (or ATLASSIAN_CLOUD_ID) so the Atlassian cloud ID can be resolved');
    const r = await request(`${new URL(site).origin}/_edge/tenant_info`);
    if (!r?.cloudId) throw new Error(`Could not read the cloud ID from ${new URL(site).origin}/_edge/tenant_info; set ATLASSIAN_CLOUD_ID`);
    return r.cloudId;
  })());
}

export async function jiraBase() {
  if (tokenType() !== 'scoped') return strip(env('JIRA_BASE_URL'));
  return `https://api.atlassian.com/ex/jira/${await cloudId()}`;
}

export async function confluenceBase() {
  if (tokenType() !== 'scoped') return env('CONFLUENCE_BASE_URL') ? strip(env('CONFLUENCE_BASE_URL')) : `${strip(env('JIRA_BASE_URL'))}/wiki`;
  return `https://api.atlassian.com/ex/confluence/${await cloudId()}/wiki`;
}

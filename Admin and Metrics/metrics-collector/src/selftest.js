// Connectivity / configuration self-test: `npm run selftest` (node src/index.js --selftest).
// Makes one tiny read-only request per configured tool and reports what is working, with a hint when not.
import { env, missingEnv, reportRange, log } from './lib/config.js';
import { createClient, basicAuth } from './lib/http.js';
import { countIssues, REQUIRED as JIRA_REQUIRED } from './clients/jira.js';
import { cqlCount, REQUIRED as CONF_REQUIRED } from './clients/confluence.js';
import { ping as bambooPing, REQUIRED as BAMBOO_REQUIRED } from './clients/bamboo.js';
import { sonar, fortify, nexusiq, dynatrace, servicenow, qmetry } from './clients/others.js';

const N = (v) => (Array.isArray(v) ? v.length : v ? 1 : 0);

const probes = [
  {
    tool: 'Jira',
    requires: JIRA_REQUIRED.concat('JIRA_SCOPE_JQL'),
    run: async () => `${await countIssues(env('JIRA_SCOPE_JQL'))} issue(s) match JIRA_SCOPE_JQL`,
  },
  {
    tool: 'Confluence',
    requires: [...CONF_REQUIRED, 'CONFLUENCE_PRD_CQL'],
    run: async () => `${await cqlCount(env('CONFLUENCE_PRD_CQL'))} page(s) match CONFLUENCE_PRD_CQL`,
  },
  { tool: 'Bamboo', requires: BAMBOO_REQUIRED, run: async () => `server version ${(await bambooPing())?.version ?? '?'}` },
  {
    tool: 'SonarQube',
    requires: sonar.REQUIRED,
    run: async () => ((await sonar.client().get('/api/authentication/validate'))?.valid ? 'token valid' : (() => { throw new Error('token not valid'); })()),
  },
  {
    tool: 'Fortify SSC',
    requires: fortify.REQUIRED,
    run: async () => `${(await fortify.client().get('/api/v1/projectVersions', { limit: 1 }))?.count ?? '?'} project version(s) visible`,
  },
  {
    tool: 'Nexus IQ',
    requires: nexusiq.REQUIRED,
    run: async () => `${N((await nexusiq.client().get('/api/v2/organizations'))?.organizations)} organization(s) visible`,
  },
  {
    tool: 'Dynatrace',
    requires: dynatrace.REQUIRED,
    run: async () => (await dynatrace.client().get('/api/v2/problems', { pageSize: 1 }), 'problems API reachable'),
  },
  {
    tool: 'ServiceNow',
    requires: servicenow.REQUIRED,
    run: async () => (await servicenow.client().get('/api/now/table/incident', { sysparm_limit: 1, sysparm_fields: 'number' }), 'incident table readable'),
  },
  {
    tool: 'QMetry',
    requires: qmetry.REQUIRED,
    run: async () => (await qmetry.client().post('/testcases/search/', { filter: { projectId: env('QMETRY_PROJECT_ID') } }, { startAt: 0, maxResults: 1 }), 'test case search reachable (endpoint unverified)'),
  },
];

function hint(e) {
  const m = `${e.message} ${e.cause?.code ?? ''} ${e.cause?.message ?? ''}`;
  if (e.status === 401) return 'authentication failed: check the token/user, and ATLASSIAN_TOKEN_TYPE for Jira/Confluence';
  if (e.status === 403) return 'authenticated but not permitted: missing token scope or project/space permission (the message usually names it)';
  if (e.status === 404) return 'not found: check the base URL / context path (e.g. /ssc, /wiki)';
  if (/CERT|self.signed|unable to verify/i.test(m)) return 'TLS error: set NODE_EXTRA_CA_CERTS to your corporate CA';
  if (/ENOTFOUND|EAI_AGAIN/i.test(m)) return 'host not found: check the URL, VPN, and NO_PROXY';
  if (/ECONNREFUSED|ETIMEDOUT|ECONNRESET|UND_ERR_CONNECT/i.test(m)) return 'cannot connect: VPN/network/proxy (HTTPS_PROXY, NO_PROXY)';
  return undefined;
}

export async function selftest() {
  const rows = [];
  const add = (check, status, detail) => rows.push({ check, status, detail });

  const [maj, min] = process.versions.node.split('.').map(Number);
  add('Node >= 22.19', maj > 22 || (maj === 22 && min >= 19) ? 'ok' : 'FAIL', process.version);
  try {
    await import('dotenv');
    add('dotenv installed', 'ok', `ENV_FILE=${env('ENV_FILE', '.env')}`);
  } catch {
    add('dotenv installed', 'FAIL', 'run `npm install` (otherwise .env is silently ignored)');
  }
  try {
    const r = reportRange();
    add('Report window', 'ok', `${r.fromStr} -> ${r.toStr}`);
  } catch (e) {
    add('Report window', 'FAIL', e.message);
  }

  for (const p of probes) {
    const missing = missingEnv(p.requires);
    if (missing.length) {
      add(p.tool, 'skipped', `not configured (missing ${missing.join(' ')})`);
      continue;
    }
    const t0 = Date.now();
    try {
      add(p.tool, 'ok', `${await p.run()} (${Date.now() - t0}ms)`);
    } catch (e) {
      log.debug(e.stack);
      add(p.tool, 'FAIL', [e.message.split('\n')[0].slice(0, 200), hint(e)].filter(Boolean).join(' -> '));
    }
  }

  console.table(rows);
  const failed = rows.filter((r) => r.status === 'FAIL').length;
  const ok = rows.filter((r) => r.status === 'ok').length;
  console.error(failed ? `${failed} check(s) FAILED, ${ok} ok.` : `All configured checks passed (${ok} ok).`);
  return failed ? 1 : 0;
}

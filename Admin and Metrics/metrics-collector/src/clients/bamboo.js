// Atlassian Bamboo (Data Center / Server) REST API.
// Finds successful deployments to production environments and the Jira issues contained in the
// builds that were deployed (Bamboo's linked Jira issues + issue keys in commit messages).
import { env, list, num, bool, log } from '../lib/config.js';
import { createClient, basicAuth, pMap } from '../lib/http.js';
import { lc, parseDate } from '../lib/util.js';

let _c;
function client() {
  if (_c) return _c;
  const headers = env('BAMBOO_TOKEN')
    ? { Authorization: `Bearer ${env('BAMBOO_TOKEN')}` }
    : { Authorization: basicAuth(env('BAMBOO_USER'), env('BAMBOO_PASSWORD')) };
  return (_c = createClient(env('BAMBOO_URL'), headers));
}

export const REQUIRED = ['BAMBOO_URL', 'BAMBOO_TOKEN|BAMBOO_PASSWORD'];

/** Cheap authenticated call used by the self-test. */
export const ping = () => client().get('/rest/api/latest/info');

const KEY_RE = /\b[A-Z][A-Z0-9_]+-\d+\b/g;
const splitResultKey = (key) => {
  const m = /^(.+)-(\d+)$/.exec(key ?? '');
  return m ? { plan: m[1], number: Number(m[2]) } : null;
};

async function envDeployments(project, environment, range) {
  const all = [];
  const page = 100;
  const cap = num('BAMBOO_MAX_DEPLOYMENTS_PER_ENV', 2000);
  for (let start = 0; all.length < cap; ) {
    const r = await client().get(`/rest/api/latest/deploy/environment/${environment.id}/results`, {
      'max-result': page,
      'start-index': start,
    });
    const results = r?.results ?? [];
    all.push(...results);
    if (results.length < page) break;
    start += results.length;
  }
  const ok = all
    .filter((d) => d.deploymentState === 'SUCCESS')
    .map((d) => ({
      id: d.id,
      project: project.name,
      environment: environment.name,
      versionId: d.deploymentVersion?.id,
      versionName: d.deploymentVersionName ?? d.deploymentVersion?.name,
      finished: parseDate(d.finishedDate ?? d.executedDate ?? d.startedDate),
    }))
    .filter((d) => d.finished && d.finished <= range.to)
    .sort((a, b) => a.finished - b.finished);
  // keep in-range deployments plus the most recent one before the window (marks the starting build number)
  const prior = ok.filter((d) => d.finished < range.from).at(-1);
  return [...(prior ? [{ ...prior, inRange: false }] : []), ...ok.filter((d) => d.finished >= range.from).map((d) => ({ ...d, inRange: true }))];
}

/**
 * Returns { deployments: [...in-range prod deployments], firstDeploy: Map(issueKey -> deployment) }.
 * With BAMBOO_INCLUDE_INTERMEDIATE_BUILDS=true (default), issues from builds between the previously deployed
 * build and the newly deployed build of the same plan are attributed to the new deployment.
 */
export async function prodDeploymentsWithIssues(range) {
  const projFilter = list('BAMBOO_DEPLOY_PROJECTS').map(lc);
  const prodEnvs = list('BAMBOO_PROD_ENVIRONMENTS', ['Production']).map(lc);
  const keyPrefixes = list('BAMBOO_JIRA_KEY_PREFIXES').map((p) => p.toUpperCase());

  const projects = (await client().get('/rest/api/latest/deploy/project/all')) ?? [];
  const selected = projects.filter((p) => !projFilter.length || projFilter.includes(lc(p.name)) || projFilter.includes(String(p.id)));
  if (!selected.length) log.warn('Bamboo: no deployment projects matched BAMBOO_DEPLOY_PROJECTS');

  const all = [];
  for (const p of selected)
    for (const e of p.environments ?? []) if (prodEnvs.includes(lc(e.name))) all.push(...(await envDeployments(p, e, range)));
  log.info(`Bamboo: ${all.filter((d) => d.inRange).length} successful prod deployments in range across ${selected.length} project(s)`);

  // deployment version -> build result keys
  const versionCache = new Map();
  await pMap(all, async (d) => {
    if (!d.versionId) return;
    if (!versionCache.has(d.versionId))
      versionCache.set(
        d.versionId,
        client().get(`/rest/api/latest/deploy/version/${d.versionId}`).catch((e) => (log.warn(`Bamboo version ${d.versionId}: ${e.message}`), null)),
      );
    const v = await versionCache.get(d.versionId);
    d.builds = (v?.items ?? []).map((it) => it.planResultKey?.key).filter(Boolean);
  });

  // work out which builds each in-range deployment "shipped"
  const includeIntermediate = bool('BAMBOO_INCLUDE_INTERMEDIATE_BUILDS', true);
  const maxGap = num('BAMBOO_MAX_INTERMEDIATE_BUILDS', 50);
  const chains = new Map();
  for (const d of all)
    for (const b of d.builds ?? []) {
      const k = splitResultKey(b);
      if (!k) continue;
      const id = `${d.project}|${d.environment}|${k.plan}`;
      if (!chains.has(id)) chains.set(id, []);
      chains.get(id).push({ d, key: b, ...k });
    }
  const shipped = new Map();
  for (const entries of chains.values()) {
    entries.sort((a, b) => a.d.finished - b.d.finished);
    let prev = null;
    for (const e of entries) {
      if (e.d.inRange) {
        const set = shipped.get(e.d) ?? new Set();
        if (includeIntermediate && prev !== null && e.number > prev && e.number - prev <= maxGap)
          for (let n = prev + 1; n <= e.number; n++) set.add(`${e.plan}-${n}`);
        else set.add(e.key);
        shipped.set(e.d, set);
      }
      prev = prev === null ? e.number : Math.max(prev, e.number);
    }
  }

  const buildCache = new Map();
  const buildIssues = (key) => {
    if (!buildCache.has(key))
      buildCache.set(
        key,
        client()
          .get(`/rest/api/latest/result/${key}`, { expand: 'jiraIssues,changes.change' })
          .then((r) => {
            const keys = new Set();
            for (const i of r?.jiraIssues?.issue ?? r?.jiraIssues?.jiraIssue ?? []) if (i.key) keys.add(i.key);
            for (const c of r?.changes?.change ?? []) for (const m of String(c.comment ?? '').match(KEY_RE) ?? []) keys.add(m);
            return [...keys].filter((k) => !keyPrefixes.length || keyPrefixes.includes(k.split('-')[0]));
          })
          .catch((e) => {
            if (e.status !== 404) log.warn(`Bamboo build ${key}: ${e.message}`);
            return [];
          }),
      );
    return buildCache.get(key);
  };

  const firstDeploy = new Map();
  const deployments = [...shipped.keys()].sort((a, b) => a.finished - b.finished);
  for (const d of deployments) {
    const lists = await pMap([...shipped.get(d)], buildIssues);
    d.issueKeys = [...new Set(lists.flat())];
    d.buildCount = shipped.get(d).size;
    for (const k of d.issueKeys) if (!firstDeploy.has(k)) firstDeploy.set(k, d);
  }
  return { deployments: all.filter((d) => d.inRange), firstDeploy };
}

// Smaller clients: SonarQube, Fortify SSC, Nexus IQ, Dynatrace, ServiceNow, QMetry.
import { env, list, log } from '../lib/config.js';
import { createClient, basicAuth } from '../lib/http.js';
import { lc, parseDate } from '../lib/util.js';

const lazy = (factory) => {
  let c;
  return () => (c ??= factory());
};

/* ------------------------------- SonarQube -------------------------------- */
export const sonar = {
  REQUIRED: ['SONAR_URL', 'SONAR_TOKEN'],
  client: lazy(() => createClient(env('SONAR_URL'), { Authorization: basicAuth(env('SONAR_TOKEN'), '') })),

  async projectKeys() {
    const keys = list('SONAR_PROJECT_KEYS');
    if (keys.length) return keys;
    const out = [];
    for (let p = 1; ; p++) {
      const r = await this.client().get('/api/components/search', { qualifiers: 'TRK', q: env('SONAR_PROJECT_SEARCH'), ps: 500, p });
      out.push(...(r?.components ?? []).map((c) => c.key));
      if (!r?.components?.length || out.length >= (r?.paging?.total ?? 0)) break;
    }
    return out;
  },

  /** Full measure history: { metricKey: [{at, value}] } */
  async history(component, metrics) {
    const out = {};
    for (let p = 1; ; p++) {
      const r = await this.client().get('/api/measures/search_history', {
        component,
        metrics: metrics.join(','),
        ps: 1000,
        p,
        branch: env('SONAR_BRANCH'),
      });
      for (const m of r?.measures ?? [])
        (out[m.metric] ??= []).push(
          ...(m.history ?? []).filter((h) => h.value !== undefined).map((h) => ({ at: parseDate(h.date), value: Number(h.value) })),
        );
      if (p * 1000 >= (r?.paging?.total ?? 0)) break;
    }
    return out;
  },
};

/* ------------------------------ Fortify SSC ------------------------------- */
export const fortify = {
  REQUIRED: ['FORTIFY_URL', 'FORTIFY_TOKEN'],
  client: lazy(() => createClient(env('FORTIFY_URL'), { Authorization: `FortifyToken ${env('FORTIFY_TOKEN')}` })),

  async paged(path, query = {}) {
    const out = [];
    for (let start = 0; ; ) {
      const r = await this.client().get(path, { ...query, start, limit: 500 });
      const data = r?.data ?? [];
      out.push(...data);
      start += data.length;
      if (!data.length || start >= (r?.count ?? 0)) break;
    }
    return out;
  },

  /** Application versions in scope (FORTIFY_VERSION_IDS and/or FORTIFY_APPLICATIONS="App" or "App:Version"; none = all visible). */
  async versions() {
    const ids = list('FORTIFY_VERSION_IDS');
    const apps = list('FORTIFY_APPLICATIONS').map(lc);
    const all = await this.paged('/api/v1/projectVersions', { fields: 'id,name,project' });
    return all
      .filter((v) =>
        !ids.length && !apps.length
          ? true
          : ids.includes(String(v.id)) || apps.includes(lc(v.project?.name)) || apps.includes(lc(`${v.project?.name}:${v.name}`)),
      )
      .map((v) => ({ id: v.id, application: v.project?.name, version: v.name }));
  },

  /** All issues incl. removed (fixed / no longer detected); suppressed & hidden excluded. */
  issues(versionId) {
    return this.paged(`/api/v1/projectVersions/${versionId}/issues`, { showremoved: true, showsuppressed: false, showhidden: false });
  },
};

/* -------------------------------- Nexus IQ -------------------------------- */
export const nexusiq = {
  REQUIRED: ['NEXUSIQ_URL', 'NEXUSIQ_USER', 'NEXUSIQ_TOKEN'],
  client: lazy(() => createClient(env('NEXUSIQ_URL'), { Authorization: basicAuth(env('NEXUSIQ_USER'), env('NEXUSIQ_TOKEN')) })),

  async scope() {
    const orgs = list('NEXUSIQ_ORGANIZATIONS').map(lc);
    if (orgs.length) {
      const r = await this.client().get('/api/v2/organizations');
      const ids = (r?.organizations ?? []).filter((o) => orgs.includes(lc(o.name)) || orgs.includes(lc(o.id))).map((o) => o.id);
      if (!ids.length) throw new Error('No Nexus IQ organizations matched NEXUSIQ_ORGANIZATIONS');
      return { organizationIds: ids };
    }
    const pubs = list('NEXUSIQ_APPLICATIONS');
    const r = await this.client().get('/api/v2/applications', pubs.length ? { publicId: pubs } : {});
    const ids = (r?.applications ?? []).map((a) => a.id);
    if (!ids.length) throw new Error('No Nexus IQ applications found for the configured scope');
    return { applicationIds: ids };
  },

  /** Success-metrics reporting API, monthly buckets covering the report range. */
  async metrics(range) {
    const month = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
    const body = { timePeriod: 'MONTH', firstTimePeriod: month(range.from), lastTimePeriod: month(range.to), ...(await this.scope()) };
    return (await this.client().post('/api/v2/reports/metrics', body)) ?? [];
  },
};

/* -------------------------------- Dynatrace ------------------------------- */
export const dynatrace = {
  REQUIRED: ['DT_URL', 'DT_API_TOKEN'],
  client: lazy(() => createClient(env('DT_URL'), { Authorization: `Api-Token ${env('DT_API_TOKEN')}` })),

  async problems(range) {
    const out = [];
    let r = await this.client().get('/api/v2/problems', {
      from: range.from.toISOString(),
      to: range.to.toISOString(),
      pageSize: 500,
      problemSelector: env('DT_PROBLEM_SELECTOR'),
      entitySelector: env('DT_ENTITY_SELECTOR'),
    });
    for (;;) {
      out.push(...(r?.problems ?? []));
      if (!r?.nextPageKey) break;
      r = await this.client().get('/api/v2/problems', { nextPageKey: r.nextPageKey });
    }
    return out;
  },
};

/* ------------------------------- ServiceNow ------------------------------- */
export const servicenow = {
  REQUIRED: ['SNOW_URL', 'SNOW_USER|SNOW_TOKEN', 'SNOW_PASSWORD|SNOW_TOKEN'],
  client: lazy(() =>
    createClient(env('SNOW_URL'), {
      Authorization: env('SNOW_TOKEN') ? `Bearer ${env('SNOW_TOKEN')}` : basicAuth(env('SNOW_USER'), env('SNOW_PASSWORD')),
    }),
  ),

  /** Encoded-query date window (evaluated in the API user's ServiceNow time zone). */
  between: (field, range) =>
    `${field}BETWEENjavascript:gs.dateGenerate('${range.fromStr}','00:00:00')@javascript:gs.dateGenerate('${range.toStr}','23:59:59')`,
  and: (...parts) => parts.filter(Boolean).join('^'),

  async table(name, query, fields) {
    const out = [];
    const limit = 1000;
    for (let offset = 0; ; offset += limit) {
      log.debug(`SNOW ${name}: ${query}`);
      const r = await this.client().get(`/api/now/table/${name}`, {
        sysparm_query: `${query}^ORDERBYsys_created_on`,
        sysparm_fields: fields.join(','),
        sysparm_limit: limit,
        sysparm_offset: offset,
        sysparm_display_value: 'false',
        sysparm_exclude_reference_link: 'true',
      });
      const rows = r?.result ?? [];
      out.push(...rows);
      if (rows.length < limit) break;
    }
    return out;
  },
};

/* --------------------------------- QMetry --------------------------------- */
// Written for "QMetry Test Management for Jira" Cloud (QTM4J). VERIFY against your QMetry edition.
export const qmetry = {
  REQUIRED: ['QMETRY_API_KEY', 'QMETRY_PROJECT_ID'],
  client: lazy(() =>
    createClient(env('QMETRY_BASE_URL', 'https://qtmcloud.qmetry.com/rest/api/latest'), { apiKey: env('QMETRY_API_KEY') }),
  ),

  async testCases() {
    const out = [];
    const max = 100;
    for (let startAt = 0; ; startAt += max) {
      const r = await this.client().post('/testcases/search/', { filter: { projectId: env('QMETRY_PROJECT_ID') } }, { startAt, maxResults: max });
      const data = r?.data ?? [];
      out.push(...data);
      if (data.length < max || out.length >= (r?.total ?? Infinity)) break;
    }
    return out;
  },
};

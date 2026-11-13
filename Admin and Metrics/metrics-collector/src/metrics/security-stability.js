// Security (Fortify SSC), Supply Chain (Nexus IQ), Stability (ServiceNow, Dynatrace)
import { env, list, bool, log } from '../lib/config.js';
import { pMap } from '../lib/http.js';
import { fortify, nexusiq, dynatrace, servicenow as snow } from '../clients/others.js';
import { DAY, HOUR, chunk, iso, lc, parseDate, pct, round, sum, summarize } from '../lib/util.js';

/* -------------------------------- Fortify --------------------------------- */
const priorities = () => new Set(list('FORTIFY_PRIORITIES', ['Critical', 'High']).map(lc));

async function fortifyIssues() {
  const versions = await fortify.versions();
  log.info(`Fortify: ${versions.length} application version(s) in scope`);
  const per = await pMap(versions, async (v) => (await fortify.issues(v.id)).map((i) => ({ ...i, _v: v })));
  return { versions, issues: per.flat().filter((i) => priorities().has(lc(i.friority))) };
}

const fortifyCritical = {
  key: 'fortify_critical',
  name: 'Critical Fortify Findings',
  category: 'Security',
  source: 'Fortify SSC',
  requires: fortify.REQUIRED,
  async run({ range }) {
    const { versions, issues } = await fortifyIssues();
    const openAt = (t) => issues.filter((i) => {
      const found = parseDate(i.foundDate);
      const removed = i.removed ? parseDate(i.removedDate) : null;
      return found && found <= t && (!removed || removed > t);
    });
    const openEnd = openAt(range.to);
    const introduced = issues.filter((i) => {
      const f = parseDate(i.foundDate);
      return f && f >= range.from && f <= range.to;
    });
    const byPriority = Object.fromEntries([...priorities()].map((p) => [p, openEnd.filter((i) => lc(i.friority) === p).length]));
    return {
      value: openEnd.length,
      unit: 'open findings at REPORT_TO',
      summary: { versions: versions.length, openAtStart: openAt(range.from).length, openAtEnd: openEnd.length, introducedInWindow: introduced.length, byPriority },
      details: openEnd.map((i) => ({
        application: i._v.application,
        version: i._v.version,
        id: i.id,
        priority: i.friority,
        category: i.issueName,
        location: i.primaryLocation,
        line: i.lineNumber,
        found: i.foundDate,
        ageDays: round((range.to - parseDate(i.foundDate)) / DAY),
      })),
      notes: ['Uses Fortify Priority Order (friority). Suppressed/hidden issues excluded. Open-at-date reconstructed from foundDate/removedDate.'],
    };
  },
};

const vulnMttr = {
  key: 'vuln_mttr',
  name: 'Mean Time to Remediate Vulnerabilities',
  category: 'Security',
  source: 'Fortify SSC',
  requires: fortify.REQUIRED,
  async run({ range }) {
    const { issues } = await fortifyIssues();
    const fixed = issues
      .filter((i) => i.removed)
      .map((i) => ({ i, f: parseDate(i.foundDate), r: parseDate(i.removedDate) }))
      .filter(({ f, r }) => f && r && r >= range.from && r <= range.to);
    const details = fixed.map(({ i, f, r }) => ({
      application: i._v.application,
      version: i._v.version,
      id: i.id,
      priority: i.friority,
      category: i.issueName,
      found: iso(f),
      removed: iso(r),
      days: round((r - f) / DAY),
    }));
    const s = summarize(details.map((d) => d.days));
    const byPriority = Object.fromEntries([...priorities()].map((p) => [p, summarize(details.filter((d) => lc(d.priority) === p).map((d) => d.days)).mean]));
    return {
      value: s.mean,
      unit: 'days (mean)',
      summary: { ...s, meanDaysByPriority: byPriority },
      details,
      notes: ['"Remediated" = Fortify marked the issue removed (not found in a later scan). Removal can also come from code deletion or rule changes.'],
    };
  },
};

/* -------------------------------- Nexus IQ -------------------------------- */
const CATEGORIES = ['SECURITY', 'LICENSE', 'QUALITY', 'OTHER'];
const bucketSum = (obj, levels) => (obj ? sum(Object.entries(obj).filter(([k]) => !levels.length || levels.includes(k.toUpperCase())).map(([, v]) => v)) : 0);

const nexusVuln = {
  key: 'nexus_vulnerable_components',
  name: 'Vulnerable Components Introduced',
  category: 'Supply Chain',
  source: 'Nexus IQ',
  requires: nexusiq.REQUIRED,
  async run({ range }) {
    const levels = list('NEXUSIQ_THREAT_LEVELS', ['CRITICAL', 'SEVERE']).map((s) => s.toUpperCase());
    const apps = await nexusiq.metrics(range);
    const details = [];
    for (const a of apps)
      for (const g of a.aggregations ?? [])
        details.push({
          application: a.applicationPublicId ?? a.applicationName,
          organization: a.organizationName,
          period: g.timePeriodStart,
          discoveredSecurity: bucketSum(g.discoveredCounts?.SECURITY, levels),
          fixedSecurity: bucketSum(g.fixedCounts?.SECURITY, levels),
          waivedSecurity: bucketSum(g.waivedCounts?.SECURITY, levels),
          openSecurityAtPeriodEnd: bucketSum(g.openCountsAtTimePeriodEnd?.SECURITY, levels),
        });
    return {
      value: sum(details.map((d) => d.discoveredSecurity)),
      unit: `new security violations (${levels.join('/')})`,
      summary: {
        applications: apps.length,
        discovered: sum(details.map((d) => d.discoveredSecurity)),
        fixed: sum(details.map((d) => d.fixedSecurity)),
        waived: sum(details.map((d) => d.waivedSecurity)),
      },
      details,
      notes: ['Monthly buckets (whole months overlapping the window). Counts are security policy violations, a close proxy for vulnerable components.'],
    };
  },
};

const nexusPolicy = {
  key: 'nexus_policy_violations',
  name: 'Nexus Policy Violations',
  category: 'Supply Chain',
  source: 'Nexus IQ',
  requires: nexusiq.REQUIRED,
  async run({ range }) {
    const levels = list('NEXUSIQ_POLICY_THREAT_LEVELS', []).map((s) => s.toUpperCase());
    const apps = await nexusiq.metrics(range);
    const details = [];
    for (const a of apps) {
      const aggs = a.aggregations ?? [];
      const row = { application: a.applicationPublicId ?? a.applicationName, organization: a.organizationName, evaluations: sum(aggs.map((g) => g.evaluationCount)) };
      for (const c of CATEGORIES) row[`discovered_${c}`] = sum(aggs.map((g) => bucketSum(g.discoveredCounts?.[c], levels)));
      row.discoveredTotal = sum(CATEGORIES.map((c) => row[`discovered_${c}`]));
      row.openAtEnd = sum(CATEGORIES.map((c) => bucketSum(aggs.at(-1)?.openCountsAtTimePeriodEnd?.[c], levels)));
      details.push(row);
    }
    return {
      value: sum(details.map((d) => d.discoveredTotal)),
      unit: 'new policy violations',
      summary: { applications: apps.length, discovered: sum(details.map((d) => d.discoveredTotal)), openAtEnd: sum(details.map((d) => d.openAtEnd)) },
      details,
      notes: ['All policy categories (security, license, quality, other). Monthly buckets.'],
    };
  },
};

/* ------------------------------- ServiceNow ------------------------------- */
const changeFailureRate = {
  key: 'change_failure_rate',
  name: 'Change Failure Rate',
  category: 'Stability',
  source: 'ServiceNow',
  requires: snow.REQUIRED,
  async run({ range }) {
    const failedCodes = new Set(list('SNOW_FAILED_CLOSE_CODES', ['unsuccessful']).map(lc));
    const useIncidents = bool('SNOW_CFR_USE_CAUSED_INCIDENTS', true);
    const causedField = env('SNOW_INCIDENT_CAUSED_BY_FIELD', 'caused_by');
    const changes = await snow.table(
      'change_request',
      snow.and(env('SNOW_CHANGE_QUERY'), 'active=false', snow.between(env('SNOW_CHANGE_DATE_FIELD', 'closed_at'), range)),
      ['sys_id', 'number', 'short_description', 'type', 'close_code', 'closed_at', 'assignment_group', 'cmdb_ci'],
    );
    const caused = new Map();
    if (useIncidents && changes.length) {
      for (const batch of chunk(changes.map((c) => c.sys_id), 100)) {
        const rows = await snow.table('incident', `${causedField}IN${batch.join(',')}`, ['number', causedField]);
        for (const r of rows) caused.set(r[causedField], [...(caused.get(r[causedField]) ?? []), r.number]);
      }
    }
    const details = changes.map((c) => {
      const byCode = failedCodes.has(lc(c.close_code));
      const incidents = caused.get(c.sys_id) ?? [];
      return { number: c.number, type: c.type, closeCode: c.close_code, closed: c.closed_at, causedIncidents: incidents.join(' '), failed: byCode || incidents.length > 0 };
    });
    const failed = details.filter((d) => d.failed).length;
    return {
      value: pct(failed, details.length),
      unit: '%',
      summary: {
        changes: details.length,
        failed,
        failedByCloseCode: details.filter((d) => failedCodes.has(lc(d.closeCode))).length,
        failedByCausedIncident: details.filter((d) => d.causedIncidents).length,
      },
      details,
      notes: [`Failed = close_code in [${[...failedCodes].join(', ')}]${useIncidents ? ` OR an incident references it via ${causedField}` : ''}.`],
    };
  },
};

const mttr = {
  key: 'mttr',
  name: 'MTTR (Mean Time To Recovery)',
  category: 'Stability',
  source: 'ServiceNow',
  requires: snow.REQUIRED,
  async run({ range }) {
    const startF = env('SNOW_INCIDENT_START_FIELD', 'opened_at');
    const endF = env('SNOW_INCIDENT_END_FIELD', 'resolved_at');
    const rows = await snow.table(
      'incident',
      snow.and(env('SNOW_INCIDENT_QUERY', 'priority<=2'), snow.between(startF, range)),
      [...new Set(['number', 'short_description', 'priority', 'state', 'assignment_group', 'cmdb_ci', startF, endF])],
    );
    const details = rows.map((r) => {
      const s = parseDate(r[startF]);
      const e = parseDate(r[endF]);
      return { number: r.number, priority: r.priority, summary: r.short_description, start: iso(s), restored: iso(e), hours: s && e ? round((e - s) / HOUR) : null };
    });
    const s = summarize(details.map((d) => d.hours));
    return {
      value: s.mean,
      unit: 'hours (mean)',
      summary: { incidents: rows.length, unresolved: details.filter((d) => d.hours === null).length, ...s },
      details,
      notes: [`${startF} -> ${endF}. Filter: ${env('SNOW_INCIDENT_QUERY', 'priority<=2')}`],
    };
  },
};

/* -------------------------------- Dynatrace ------------------------------- */
const mttrDynatrace = {
  key: 'mttr_dynatrace',
  name: 'MTTR (Dynatrace problems)',
  category: 'Stability',
  source: 'Dynatrace',
  requires: dynatrace.REQUIRED,
  async run({ range }) {
    const sev = new Set(list('DT_SEVERITY_LEVELS', []).map((s) => s.toUpperCase()));
    const problems = (await dynatrace.problems(range)).filter((p) => (!sev.size || sev.has(p.severityLevel)) && p.startTime >= range.from.getTime() && p.startTime <= range.to.getTime());
    const details = problems.map((p) => ({
      id: p.displayId ?? p.problemId,
      title: p.title,
      severity: p.severityLevel,
      impact: p.impactLevel,
      status: p.status,
      start: iso(p.startTime),
      end: p.endTime > 0 ? iso(p.endTime) : '',
      hours: p.endTime > 0 ? round((p.endTime - p.startTime) / HOUR) : null,
    }));
    const s = summarize(details.map((d) => d.hours));
    return { value: s.mean, unit: 'hours (mean)', summary: { problems: problems.length, open: details.filter((d) => d.hours === null).length, ...s }, details, notes: [] };
  },
};

export default [fortifyCritical, vulnMttr, nexusVuln, nexusPolicy, changeFailureRate, mttr, mttrDynatrace];

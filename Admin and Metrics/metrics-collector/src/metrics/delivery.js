// Development Speed + Quality + QE Effectiveness (Jira, Bamboo, SonarQube, QMetry)
import { env, list, log } from '../lib/config.js';
import * as jira from '../clients/jira.js';
import * as bamboo from '../clients/bamboo.js';
import { sonar, qmetry } from '../clients/others.js';
import { DAY, iso, lc, parseDate, pct, round, summarize } from '../lib/util.js';

const JIRA = [...jira.REQUIRED, 'JIRA_SCOPE_JQL'];
const createdIn = (r) => `created >= "${r.fromStr}" AND created < "${r.toExclusiveStr}"`;
const defectTypes = () => jira.jqlList(list('JIRA_DEFECT_TYPES', ['Bug']));

/* ----------------------------- Cycle Time ----------------------------- */
const cycleTime = {
  key: 'cycle_time',
  name: 'Cycle Time',
  category: 'Development Speed',
  source: 'Jira',
  requires: JIRA,
  async run({ range }) {
    const startSet = new Set(list('JIRA_START_STATUSES', ['In Progress']).map(lc));
    const doneStatuses = list('JIRA_DONE_STATUSES', ['Done']);
    const doneSet = new Set(doneStatuses.map(lc));
    const jql = jira.scoped(
      env('JIRA_WORK_ITEM_JQL'),
      `status CHANGED TO (${jira.jqlList(doneStatuses)}) DURING ("${range.fromStr}", "${range.toExclusiveStr}")`,
    );
    const issues = await jira.searchIssues(jql, ['issuetype', 'summary', 'created']);
    const logs = await jira.changelogs(issues.map((i) => i.id), ['status']);
    const details = [];
    let excluded = 0;
    for (const i of issues) {
      const t = jira.transitions(logs.get(String(i.id)), 'status');
      const start = t.find((x) => startSet.has(lc(x.to)))?.at;
      const end = t.filter((x) => doneSet.has(lc(x.to)) && x.at >= range.from && x.at <= range.to).at(-1)?.at;
      if (!start || !end || end < start) {
        excluded++;
        continue;
      }
      details.push({
        key: i.key,
        type: i.fields?.issuetype?.name,
        summary: i.fields?.summary,
        started: iso(start),
        done: iso(end),
        days: round((end - start) / DAY),
      });
    }
    const s = summarize(details.map((d) => d.days));
    return {
      value: s.mean,
      unit: 'days (mean)',
      summary: { ...s, issuesCompleted: issues.length, excludedNoStartTransition: excluded },
      details,
      notes: [`Start = first move into ${[...startSet].join('/')}; end = last move into ${doneStatuses.join('/')} within the window.`],
    };
  },
};

/* --------------------------- Lead Time for Change --------------------------- */
const leadMode = () => lc(env('LEAD_TIME_MODE', env('BAMBOO_URL') ? 'bamboo' : 'fixversion'));
const leadTime = {
  key: 'lead_time',
  name: 'Lead Time for Change',
  category: 'Development Speed',
  source: 'Jira + Bamboo',
  requires: () => (leadMode() === 'bamboo' ? [...JIRA, ...bamboo.REQUIRED] : JIRA),
  async run({ range }) {
    const mode = leadMode();
    const startSpec = env('LEAD_TIME_START', 'created');
    const fields = ['issuetype', 'summary', 'created', 'fixVersions'];
    let issues = [];
    const endAt = new Map();
    const where = new Map();
    const summaryExtra = {};

    if (mode === 'bamboo') {
      const { deployments, firstDeploy } = await bamboo.prodDeploymentsWithIssues(range);
      summaryExtra.prodDeployments = deployments.length;
      summaryExtra.deploymentsPerWeek = round(deployments.length / ((range.to - range.from) / (7 * DAY)));
      const found = await jira.bulkFetch([...firstDeploy.keys()], fields);
      let inScope = found;
      if (env('JIRA_SCOPE_JQL') || env('JIRA_WORK_ITEM_JQL')) {
        const allowed = new Set();
        for (let i = 0; i < found.length; i += 100) {
          const keys = found.slice(i, i + 100).map((x) => x.key).join(', ');
          for (const x of await jira.searchIssues(jira.scoped(env('JIRA_WORK_ITEM_JQL'), `key in (${keys})`), ['key'])) allowed.add(x.key);
        }
        inScope = found.filter((x) => allowed.has(x.key));
      }
      issues = inScope;
      for (const i of issues) {
        const d = firstDeploy.get(i.key);
        endAt.set(i.key, d.finished);
        where.set(i.key, `${d.project} / ${d.environment} / ${d.versionName}`);
      }
      summaryExtra.issueKeysFoundInBuilds = firstDeploy.size;
    } else if (mode === 'fixversion') {
      const lookback = new Date(range.from.getTime() - Number(env('LEAD_TIME_LOOKBACK_DAYS', 365)) * DAY);
      const jql = jira.scoped(env('JIRA_WORK_ITEM_JQL'), 'fixVersion in releasedVersions()', `resolved >= "${lookback.toISOString().slice(0, 10)}"`);
      for (const i of await jira.searchIssues(jql, fields)) {
        const dates = (i.fields?.fixVersions ?? [])
          .filter((v) => v.released && v.releaseDate)
          .map((v) => ({ v, at: new Date(`${v.releaseDate}T23:59:59`) }))
          .sort((a, b) => a.at - b.at);
        const first = dates[0];
        if (first && first.at >= range.from && first.at <= range.to) {
          issues.push(i);
          endAt.set(i.key, first.at);
          where.set(i.key, `fixVersion ${first.v.name}`);
        }
      }
    } else throw new Error(`Unknown LEAD_TIME_MODE "${mode}" (use bamboo | fixversion)`);

    const startAt = await jira.eventTimes(issues, startSpec);
    const details = [];
    let excluded = 0;
    for (const i of issues) {
      const s = startAt.get(i.key);
      const e = endAt.get(i.key);
      if (!s || !e || e < s) {
        excluded++;
        continue;
      }
      details.push({ key: i.key, type: i.fields?.issuetype?.name, summary: i.fields?.summary, start: iso(s), deployed: iso(e), deployedVia: where.get(i.key), days: round((e - s) / DAY) });
    }
    const s = summarize(details.map((d) => d.days));
    return {
      value: s.mean,
      unit: 'days (mean)',
      summary: { mode, startSpec, ...s, excludedNoStart: excluded, ...summaryExtra },
      details,
      notes: [
        mode === 'bamboo'
          ? 'End = first successful Bamboo deployment to a production environment whose build(s) reference the issue key.'
          : 'End = release date of the first released fixVersion (date-only, end of day). Proxy for production deployment.',
      ],
    };
  },
};

/* --------------------------- Defect Escape Rate --------------------------- */
const defectEscape = {
  key: 'defect_escape_rate',
  name: 'Defect Escape Rate',
  category: 'Quality',
  source: 'Jira',
  requires: [...JIRA, 'JIRA_ESCAPED_DEFECT_JQL'],
  async run({ range }) {
    const base = jira.scoped(`issuetype in (${defectTypes()})`, createdIn(range));
    const total = await jira.countIssues(base);
    const escaped = await jira.searchIssues(jira.and(base, env('JIRA_ESCAPED_DEFECT_JQL')), ['summary', 'priority', 'created']);
    return {
      value: pct(escaped.length, total),
      unit: '%',
      summary: { totalDefects: total, escapedDefects: escaped.length },
      details: escaped.map((i) => ({ key: i.key, summary: i.fields?.summary, priority: i.fields?.priority?.name, created: i.fields?.created })),
      notes: [`Escaped = defects matching: ${env('JIRA_ESCAPED_DEFECT_JQL')}`],
    };
  },
};

/* --------------------------- Regression Defects --------------------------- */
const regression = {
  key: 'regression_defects',
  name: 'Regression Defects per Release',
  category: 'QE Effectiveness',
  source: 'Jira',
  requires: [...JIRA, 'JIRA_REGRESSION_JQL'],
  async run({ range }) {
    const groupBy = lc(env('JIRA_REGRESSION_GROUP_BY', 'affectedVersion'));
    const field = groupBy === 'fixversion' ? 'fixVersions' : 'versions';
    const jql = jira.scoped(`issuetype in (${defectTypes()})`, createdIn(range), env('JIRA_REGRESSION_JQL'));
    const issues = await jira.searchIssues(jql, ['summary', 'fixVersions', 'versions']);
    const counts = new Map();
    for (const i of issues) {
      const versions = (i.fields?.[field] ?? []).map((v) => v.name);
      for (const v of versions.length ? versions : ['(no version)']) counts.set(v, (counts.get(v) ?? 0) + 1);
    }
    const perRelease = [...counts].filter(([v]) => v !== '(no version)').map(([, n]) => n);
    return {
      value: summarize(perRelease).mean,
      unit: 'regression defects per release (mean)',
      summary: { totalRegressionDefects: issues.length, releases: perRelease.length, withoutVersion: counts.get('(no version)') ?? 0, groupedBy: field },
      details: [...counts].map(([release, count]) => ({ release, count })).sort((a, b) => b.count - a.count),
      notes: ['Releases with zero regression defects are not listed, so the mean is over releases with >= 1.'],
    };
  },
};

/* ------------------------ SonarQube Maintainability ------------------------ */
const LETTER = ['A', 'B', 'C', 'D', 'E'];
const sonarMaint = {
  key: 'sonar_maintainability',
  name: 'SonarQube Maintainability Rating',
  category: 'Quality',
  source: 'SonarQube',
  requires: sonar.REQUIRED,
  async run({ range }) {
    const keys = await sonar.projectKeys();
    const details = [];
    for (const k of keys) {
      try {
        const h = await sonar.history(k, ['sqale_rating', 'sqale_debt_ratio']);
        const asOf = (series, t) => (series ?? []).filter((x) => x.at <= t).at(-1)?.value ?? null;
        const rs = asOf(h.sqale_rating, range.from);
        const re = asOf(h.sqale_rating, range.to);
        details.push({
          project: k,
          ratingStart: rs ? LETTER[Math.round(rs) - 1] : '',
          ratingEnd: re ? LETTER[Math.round(re) - 1] : '',
          debtRatioStart: asOf(h.sqale_debt_ratio, range.from),
          debtRatioEnd: asOf(h.sqale_debt_ratio, range.to),
          trend: rs && re ? (re < rs ? 'improved' : re > rs ? 'worsened' : 'unchanged') : 'n/a',
        });
      } catch (e) {
        details.push({ project: k, error: e.message });
      }
    }
    const dist = Object.fromEntries(LETTER.map((l) => [l, details.filter((d) => d.ratingEnd === l).length]));
    const ends = details.map((d) => LETTER.indexOf(d.ratingEnd) + 1).filter((n) => n > 0);
    return {
      value: Object.entries(dist).map(([l, n]) => `${l}:${n}`).join(' '),
      unit: 'projects by rating at REPORT_TO',
      summary: {
        projects: keys.length,
        distribution: dist,
        meanRatingEnd: ends.length ? LETTER[Math.round(ends.reduce((a, b) => a + b, 0) / ends.length) - 1] : null,
        improved: details.filter((d) => d.trend === 'improved').length,
        worsened: details.filter((d) => d.trend === 'worsened').length,
      },
      details,
      notes: ['Ratings are the latest analysis on or before each window boundary.'],
    };
  },
};

/* --------------------- Automated Critical Path Coverage --------------------- */
const critPath = {
  key: 'critical_path_coverage',
  name: 'Automated Critical Path Coverage',
  category: 'QE Effectiveness',
  source: 'QMetry',
  requires: qmetry.REQUIRED,
  async run() {
    const all = await qmetry.testCases();
    return {
      value: pct(0, all.length),
      unit: '%',
      summary: { totalTestCases: all.length, criticalPath: all.length, criticalPathAutomated: 0, manualOnly: true },
      details: all.map((tc) => ({ key: tc.key, summary: tc.summary, criticalPath: true, automated: false })),
      notes: ['Snapshot as of run time (not windowed). All test cases in the configured QMetry project are treated as critical; testing is manual-only. QMetry endpoint/fields unverified - check against your QMetry edition.'],
    };
  },
};

export default [leadTime, cycleTime, defectEscape, sonarMaint, regression, critPath];

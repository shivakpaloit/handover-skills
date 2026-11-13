// Requirements Engineering / Gen-e2 adoption (Jira, Jira Product Discovery, Confluence)
import { env, list, num, log } from '../lib/config.js';
import { pMap } from '../lib/http.js';
import { progress } from '../lib/progress.js';
import * as jira from '../clients/jira.js';
import * as confluence from '../clients/confluence.js';
import { DEFAULT_PATTERN, inWindow, primaryPrd } from '../lib/prd.js';
import { DAY, chunk, htmlToText, iso, lc, parseDate, pct, round, similarity, summarize } from '../lib/util.js';

const createdJql = (r) => `created >= "${r.fromStr}" AND created < "${r.toExclusiveStr}"`;
const createdCql = (r) => `created >= "${r.fromStr}" AND created < "${r.toExclusiveStr}"`;
const storyTypes = () => jira.jqlList(list('JIRA_STORY_TYPES', ['Story']));
const gene2Jql = () => env('GENE2_JIRA_JQL', 'labels = "aisdlc"');
const gene2Label = () => env('GENE2_CONFLUENCE_LABEL', 'aisdlc');
// PRD_SOURCE: epic (markdown attached to Jira epics) | confluence | jpd. Default: confluence/jpd if configured, else epic.
const prdSource = () =>
  lc(env('PRD_SOURCE', env('CONFLUENCE_PRD_CQL') ? 'confluence' : env('JPD_IDEAS_JQL') ? 'jpd' : 'epic'));
const prdRequires = () =>
  prdSource() === 'jpd'
    ? [...jira.REQUIRED, 'JPD_IDEAS_JQL']
    : prdSource() === 'epic'
      ? [...jira.REQUIRED, 'JIRA_SCOPE_JQL']
      : [...confluence.REQUIRED, 'CONFLUENCE_PRD_CQL'];

/* ------------- PRDs as markdown attachments on epics (PRD_SOURCE=epic) ------------- */
const EPIC_FIELDS = ['summary', 'created', 'labels', 'attachment'];
const epicBase = () => jira.scoped(env('PRD_EPIC_JQL', 'issuetype = Epic'), 'attachments is not EMPTY');

/** Epics whose PRD attachment was first uploaded in the window, flagged when they match the Gen-e2 JQL. */
async function epicPrds(range) {
  const pattern = env('PRD_ATTACHMENT_PATTERN', DEFAULT_PATTERN);
  const epics = await jira.searchIssues(epicBase(), EPIC_FIELDS);
  const gen = new Set((await jira.searchIssues(jira.and(epicBase(), gene2Jql()), ['key'])).map((i) => i.key));
  return epics
    .map((e) => ({ id: e.id, key: e.key, summary: e.fields?.summary, prd: primaryPrd(e, pattern), gene2: gen.has(e.key) }))
    .filter((e) => inWindow(e.prd, range));
}

/* ---------------------------- Gen-e2 PRD rate ---------------------------- */
const prdRate = {
  key: 'gene2_prd_rate',
  name: 'Gen-e2 Generated PRD Rate',
  category: 'Requirements Engineering',
  source: 'Epic attachments / Confluence / JPD',
  requires: prdRequires,
  async run({ range }) {
    let total, gen, details = [];
    if (prdSource() === 'epic') {
      const prds = await epicPrds(range);
      const gen = prds.filter((p) => p.gene2);
      return {
        value: pct(gen.length, prds.length),
        unit: '%',
        summary: { source: 'epic', totalPrds: prds.length, gene2Prds: gen.length },
        details: prds.map((p) => ({ epic: p.key, title: p.summary, prdFile: p.prd.filename, firstUploaded: iso(p.prd.first.created), versions: p.prd.versions.length, gene2: p.gene2 })),
        notes: [`PRD = first markdown attachment (PRD_ATTACHMENT_PATTERN=${env('PRD_ATTACHMENT_PATTERN', DEFAULT_PATTERN)}) on an epic, counted by upload date; Gen-e2 = epic matching ${gene2Jql()}.`],
      };
    }
    if (prdSource() === 'jpd') {
      const base = jira.and(env('JPD_IDEAS_JQL'), createdJql(range));
      total = await jira.countIssues(base);
      const g = await jira.searchIssues(jira.and(base, gene2Jql()), ['summary', 'created']);
      gen = g.length;
      details = g.map((i) => ({ key: i.key, summary: i.fields?.summary, created: i.fields?.created }));
    } else {
      const base = `type = page AND (${env('CONFLUENCE_PRD_CQL')}) AND ${createdCql(range)}`;
      total = await confluence.cqlCount(base);
      const pages = await confluence.cqlPages(`${base} AND label = "${gene2Label()}"`);
      gen = pages.length;
      details = pages.map((p) => ({ id: p.id, title: p.title, created: p.history?.createdDate }));
    }
    return { value: pct(gen, total), unit: '%', summary: { source: prdSource(), totalPrds: total, gene2Prds: gen }, details, notes: [] };
  },
};

/* --------------------------- Gen-e2 story rate --------------------------- */
const storyRate = {
  key: 'gene2_story_rate',
  name: 'Gen-e2 Generated User Story Rate',
  category: 'Requirements Engineering',
  source: 'Jira',
  requires: [...jira.REQUIRED, 'JIRA_SCOPE_JQL'],
  async run({ range }) {
    const base = jira.scoped(`issuetype in (${storyTypes()})`, createdJql(range));
    const total = await jira.countIssues(base);
    const gen = await jira.searchIssues(jira.and(base, gene2Jql()), ['summary', 'created']);
    return {
      value: pct(gen.length, total),
      unit: '%',
      summary: { totalStories: total, gene2Stories: gen.length },
      details: gen.map((i) => ({ key: i.key, summary: i.fields?.summary, created: i.fields?.created })),
      notes: [`Gen-e2 stories identified by: ${gene2Jql()}`],
    };
  },
};

/* ------------------------- PRD-to-Story Lead Time ------------------------- */
const prdToStory = {
  key: 'prd_to_story_lead_time',
  name: 'PRD-to-Story Lead Time',
  category: 'Requirements Engineering',
  source: 'Jira (epics) / JPD / Confluence',
  requires: () => [...new Set([...prdRequires(), ...jira.REQUIRED, 'JIRA_SCOPE_JQL'])],
  async run({ range }) {
    const readySpec = env('STORY_READY_AT', 'created');
    const storyTypeSet = new Set(list('JIRA_STORY_TYPES', ['Story']).map(lc));
    const prds = []; // {id, title, approvedAt, storyKeys[]}
    let preloaded; // stories already fetched with their created date (epic mode)

    if (prdSource() === 'epic') {
      // Stories are children of the epic that holds the PRD. Start = first PRD upload (or PRD_APPROVED_AT=status:X|Y on the epic).
      const epics = await epicPrds(range);
      const approvedSpec = env('PRD_APPROVED_AT', 'attachment');
      const approved = /^status:/i.test(approvedSpec)
        ? await jira.eventTimes(epics.map((e) => ({ key: e.key, id: e.id })), approvedSpec)
        : new Map(epics.map((e) => [e.key, e.prd.first.created]));
      const byKey = new Map(epics.map((e) => [e.key, { id: e.key, title: e.summary, approvedAt: approved.get(e.key), storyKeys: [] }]));
      preloaded = [];
      for (const batch of chunk(epics.map((e) => e.key), 100)) {
        const kids = await jira.searchIssues(jira.and(`parent in (${batch.join(',')})`, `issuetype in (${storyTypes()})`), ['created', 'issuetype', 'parent']);
        for (const k of kids) {
          byKey.get(k.fields?.parent?.key)?.storyKeys.push(k.key);
          preloaded.push(k);
        }
      }
      prds.push(...byKey.values());
    } else if (prdSource() === 'jpd') {
      const approved = list('JPD_APPROVED_STATUSES');
      if (!approved.length) throw new Error('Set JPD_APPROVED_STATUSES (the JPD status(es) meaning "approved")');
      const linkTypes = new Set(list('JPD_DELIVERY_LINK_TYPES').map(lc));
      const ideas = await jira.searchIssues(
        jira.and(env('JPD_IDEAS_JQL'), `status CHANGED TO (${jira.jqlList(approved)}) DURING ("${range.fromStr}", "${range.toExclusiveStr}")`),
        ['summary', 'issuelinks'],
      );
      const at = await jira.eventTimes(ideas, `status:${approved.join('|')}`);
      for (const i of ideas) {
        const keys = (i.fields?.issuelinks ?? [])
          .filter((l) => !linkTypes.size || linkTypes.has(lc(l.type?.name)))
          .map((l) => (l.outwardIssue ?? l.inwardIssue)?.key)
          .filter(Boolean);
        prds.push({ id: i.key, title: i.fields?.summary, approvedAt: at.get(i.key), storyKeys: keys });
      }
    } else {
      // Confluence PRDs; stories linked via Jira remote links ("mentioned in" / linked Confluence pages)
      const pages = await confluence.cqlPages(`type = page AND (${env('CONFLUENCE_PRD_CQL')}) AND ${createdCql(range)}`);
      const byId = new Map(pages.map((p) => [String(p.id), { id: String(p.id), title: p.title, approvedAt: parseDate(p.history?.createdDate), storyKeys: [] }]));
      const lookahead = num('PRD_STORY_LOOKAHEAD_DAYS', 120);
      const until = new Date(Math.min(Date.now(), range.to.getTime() + lookahead * DAY)).toISOString().slice(0, 10);
      const stories = await jira.searchIssues(jira.scoped(`issuetype in (${storyTypes()})`, `created >= "${range.fromStr}" AND created <= "${until}"`), ['key']);
      log.info(`PRD-to-story: checking remote links on ${stories.length} stories`);
      const tick = progress('Jira remote links', stories.length);
      await pMap(stories, async (s) => {
        const links = (await jira.remoteLinks(s.key).catch(() => [])) ?? [];
        tick();
        for (const l of links) {
          const m = /pageId=(\d+)|\/pages\/(\d+)/.exec(l.object?.url ?? '');
          const pid = m?.[1] ?? m?.[2];
          if (pid && byId.has(pid)) byId.get(pid).storyKeys.push(s.key);
        }
      });
      prds.push(...byId.values());
    }

    const allKeys = [...new Set(prds.flatMap((p) => p.storyKeys))];
    const stories = (preloaded ?? (await jira.bulkFetch(allKeys, ['created', 'issuetype']))).filter((s) => storyTypeSet.has(lc(s.fields?.issuetype?.name)));
    const readyAt = await jira.eventTimes(stories, readySpec);
    const details = prds.map((p) => {
      const times = p.storyKeys.map((k) => readyAt.get(k)).filter(Boolean).sort((a, b) => a - b);
      const first = times[0];
      return {
        prd: p.id,
        title: p.title,
        approved: iso(p.approvedAt),
        stories: times.length,
        firstStoryReady: iso(first),
        days: first && p.approvedAt ? round((first - p.approvedAt) / DAY) : null,
      };
    });
    const valid = details.filter((d) => d.days !== null && d.days >= 0);
    const s = summarize(valid.map((d) => d.days));
    return {
      value: s.mean,
      unit: 'days (mean)',
      summary: {
        source: prdSource(),
        prds: prds.length,
        withStories: details.filter((d) => d.stories).length,
        storiesBeforeApproval: details.filter((d) => d.days !== null && d.days < 0).length,
        ...s,
      },
      details,
      notes: [
        prdSource() === 'epic'
          ? env('PRD_APPROVED_AT', 'attachment') === 'attachment'
            ? 'Start = first upload of the PRD markdown attachment on the epic (proxy for approval; set PRD_APPROVED_AT=status:Approved to use an epic status instead).'
            : `Start = epic reaching ${env('PRD_APPROVED_AT')}.`
          : prdSource() === 'jpd'
            ? 'Start = first transition of the JPD idea into JPD_APPROVED_STATUSES.'
            : 'Start = PRD page creation date (proxy - Confluence does not expose an approval timestamp via API).',
        `End = earliest linked story ${readySpec === 'created' ? 'creation' : `reaching ${readySpec}`}.`,
      ],
    };
  },
};

/* ------------------------ Gen-e2 Acceptance Rate ------------------------ */
const acceptance = {
  key: 'gene2_acceptance_rate',
  name: 'Gen-e2 Requirements Acceptance Rate',
  category: 'Requirements Engineering',
  source: 'Jira (+ epic attachments / Confluence)',
  requires: [...jira.REQUIRED, 'JIRA_SCOPE_JQL'],
  async run({ range }) {
    const threshold = num('GENE2_ACCEPT_THRESHOLD', 0.8);
    const details = [];

    // Epic PRDs: compare the first upload of the PRD file with the latest upload of the same file name
    if (prdSource() === 'epic') {
      const prds = (await epicPrds(range)).filter((p) => p.gene2);
      const tick = progress('PRD attachment downloads', prds.length);
      await pMap(prds, async (p) => {
        const { versions, first, current } = p.prd;
        try {
          let sim = 1; // never re-uploaded: no recorded rework
          if (versions.length > 1) sim = similarity(String((await jira.attachmentText(first.id)) ?? ''), String((await jira.attachmentText(current.id)) ?? ''));
          details.push({ kind: 'PRD', id: p.key, title: p.summary, versions: versions.length, similarity: round(sim, 3), accepted: sim >= threshold });
        } catch (e) {
          details.push({ kind: 'PRD', id: p.key, title: p.summary, error: e.message });
        }
        tick();
      });
    } else if (env('CONFLUENCE_PRD_CQL') || env('GENE2_CONFLUENCE_CQL')) {
      const cql = `type = page AND label = "${gene2Label()}" AND ${createdCql(range)}${env('CONFLUENCE_PRD_CQL') ? ` AND (${env('CONFLUENCE_PRD_CQL')})` : ''}${env('GENE2_CONFLUENCE_CQL') ? ` AND (${env('GENE2_CONFLUENCE_CQL')})` : ''}`;
      const pages = await confluence.cqlPages(cql, 'history,version');
      await pMap(pages, async (p) => {
        try {
          const [v1, cur] = await Promise.all([confluence.pageBody(p.id, 1), confluence.pageBody(p.id)]);
          const sim = similarity(htmlToText(v1.body), htmlToText(cur.body));
          details.push({ kind: 'PRD', id: p.id, title: p.title, versions: cur.version, similarity: round(sim, 3), accepted: sim >= threshold });
        } catch (e) {
          details.push({ kind: 'PRD', id: p.id, title: p.title, error: e.message });
        }
      });
    }

    // Jira stories: compare the first description with the current one (from the changelog)
    const stories = await jira.searchIssues(jira.scoped(`issuetype in (${storyTypes()})`, createdJql(range), gene2Jql()), ['summary', 'created']);
    const logs = await jira.changelogs(stories.map((s) => s.id), ['description']);
    for (const s of stories) {
      const t = jira.transitions(logs.get(String(s.id)), 'description');
      const original = t[0]?.from ?? t[0]?.to ?? '';
      const current = t.at(-1)?.to ?? '';
      const sim = t.length ? similarity(original, current) : 1;
      details.push({ kind: 'Story', id: s.key, title: s.fields?.summary, edits: t.length, similarity: round(sim, 3), accepted: sim >= threshold });
    }

    const scored = details.filter((d) => d.similarity !== undefined);
    const ok = scored.filter((d) => d.accepted).length;
    const prd = scored.filter((d) => d.kind === 'PRD');
    const st = scored.filter((d) => d.kind === 'Story');
    return {
      value: pct(ok, scored.length),
      unit: '%',
      summary: {
        threshold,
        artefacts: scored.length,
        accepted: ok,
        prdAcceptanceRate: pct(prd.filter((d) => d.accepted).length, prd.length),
        storyAcceptanceRate: pct(st.filter((d) => d.accepted).length, st.length),
        meanSimilarity: summarize(scored.map((d) => d.similarity)).mean,
      },
      details,
      notes: [
        `"Accepted with minimal rework" = text similarity between first and current version >= ${threshold}.`,
        'Assumes the Gen-e2 output is the first saved version (first attachment upload / Confluence v1 / initial Jira description). Epic PRDs count a re-upload of the same file name as a new version; a PRD edited in place or never re-uploaded counts as accepted.',
      ],
    };
  },
};

export default [prdRate, storyRate, prdToStory, acceptance];

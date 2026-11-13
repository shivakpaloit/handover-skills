// End-to-end check of the PRD_SOURCE=epic metrics against a mock Jira server (no network, no credentials).
import test, { before, after } from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';

const att = (id, filename, created) => ({ id, filename, created });
const EPICS = [
  // E1: Gen-e2 PRD, uploaded twice (draft then edited), two child stories
  { id: '1', key: 'T-1', fields: { summary: 'Gen-e2 epic', created: '2026-08-20T09:00:00.000+0800', labels: ['aisdlc'], attachment: [att('11', 'prd.md', '2026-09-01T10:00:00.000+0800'), att('12', 'prd.md', '2026-09-10T10:00:00.000+0800'), att('13', 'arch.png', '2026-09-02T10:00:00.000+0800')] } },
  // E2: hand-written PRD, uploaded once, no stories
  { id: '2', key: 'T-2', fields: { summary: 'Manual epic', created: '2026-08-21T09:00:00.000+0800', labels: [], attachment: [att('21', 'PRD.md', '2026-09-05T10:00:00.000+0800')] } },
  // E3: Gen-e2 PRD uploaded before the window, must be ignored
  { id: '3', key: 'T-3', fields: { summary: 'Old epic', created: '2026-05-01T09:00:00.000+0800', labels: ['aisdlc'], attachment: [att('31', 'prd.md', '2026-06-01T10:00:00.000+0800')] } },
];
const KIDS = [
  { id: '101', key: 'T-101', fields: { created: '2026-09-03T10:00:00.000+0800', issuetype: { name: 'Story' }, parent: { key: 'T-1' } } },
  { id: '102', key: 'T-102', fields: { created: '2026-09-08T10:00:00.000+0800', issuetype: { name: 'Story' }, parent: { key: 'T-1' } } },
];
const TEXT = { 11: '# PRD\n\nThe system shall export metrics.\nIt shall log requests.\nIt shall retry failures.\n', 12: '# PRD\n\nThe system shall export metrics.\nIt shall log requests and responses.\nIt shall retry failures with backoff.\nIt shall page results.\n' };

let server;
let metrics;
const range = { fromStr: '2026-08-01', toStr: '2026-11-12', toExclusiveStr: '2026-11-13', from: new Date('2026-08-01T00:00:00+08:00'), to: new Date('2026-11-12T23:59:59+08:00') };
const run = (key) => metrics.find((m) => m.key === key).run({ range });

before(async () => {
  server = http.createServer((req, res) => {
    let body = '';
    req.on('data', (c) => (body += c));
    req.on('end', () => {
      const send = (obj) => (res.setHeader('content-type', 'application/json'), res.end(JSON.stringify(obj)));
      const url = req.url;
      if (url.startsWith('/rest/api/3/attachment/content/')) return res.end(TEXT[url.split('/').pop()] ?? '');
      if (url.startsWith('/rest/api/3/search/approximate-count')) return send({ count: 0 });
      if (url.startsWith('/rest/api/3/changelog/bulkfetch')) return send({ issueChangeLogs: [] });
      if (url.startsWith('/rest/api/3/search/jql')) {
        const { jql } = JSON.parse(body);
        let issues = [];
        if (jql.includes('parent in')) issues = KIDS;
        else if (jql.includes('attachments is not EMPTY')) issues = jql.includes('aisdlc') ? EPICS.filter((e) => e.fields.labels.includes('aisdlc')) : EPICS;
        return send({ issues, isLast: true });
      }
      res.statusCode = 404;
      res.end('{}');
    });
  });
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  Object.assign(process.env, {
    ATLASSIAN_TOKEN_TYPE: 'classic',
    JIRA_BASE_URL: `http://127.0.0.1:${server.address().port}`,
    JIRA_EMAIL: 'a@b.c',
    JIRA_API_TOKEN: 'x',
    JIRA_SCOPE_JQL: 'project = T',
    PRD_SOURCE: 'epic',
    JIRA_STORY_TYPES: 'Story',
    HTTP_RETRIES: '0',
  });
  metrics = (await import('../src/metrics/requirements.js')).default;
});

after(() => server.close());

test('gene2_prd_rate counts epics by first PRD upload in the window', async () => {
  const r = await run('gene2_prd_rate');
  assert.equal(r.summary.totalPrds, 2); // E3 uploaded before the window
  assert.equal(r.summary.gene2Prds, 1);
  assert.equal(r.value, 50);
  assert.deepEqual(r.details.map((d) => d.epic).sort(), ['T-1', 'T-2']);
});

test('prd_to_story_lead_time runs from first PRD upload to the first child story', async () => {
  const r = await run('prd_to_story_lead_time');
  assert.equal(r.summary.prds, 2);
  assert.equal(r.summary.withStories, 1);
  assert.equal(r.value, 2); // 2026-09-01 10:00 -> 2026-09-03 10:00
});

test('gene2_acceptance_rate compares first and latest upload of the Gen-e2 PRD', async () => {
  const r = await run('gene2_acceptance_rate');
  const prd = r.details.filter((d) => d.kind === 'PRD');
  assert.equal(prd.length, 1); // only the Gen-e2 epic in the window
  assert.equal(prd[0].id, 'T-1');
  assert.equal(prd[0].versions, 2);
  assert.ok(prd[0].similarity > 0 && prd[0].similarity < 1, `similarity ${prd[0].similarity}`);
});

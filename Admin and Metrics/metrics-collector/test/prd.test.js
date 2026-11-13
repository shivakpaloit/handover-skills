import test from 'node:test';
import assert from 'node:assert/strict';
import { primaryPrd, inWindow } from '../src/lib/prd.js';

const att = (id, filename, created) => ({ id, filename, created });
const epic = (...attachment) => ({ fields: { attachment } });
const range = { from: new Date('2026-08-01T00:00:00'), to: new Date('2026-11-12T23:59:59') };

test('no markdown attachment means no PRD', () => {
  assert.equal(primaryPrd(epic(att(1, 'diagram.png', '2026-09-01T10:00:00.000+0800'))), null);
  assert.equal(primaryPrd(epic()), null);
  assert.equal(primaryPrd({ fields: {} }), null);
});

test('single markdown attachment is both first and current', () => {
  const p = primaryPrd(epic(att(1, 'PRD.md', '2026-09-01T10:00:00.000+0800')));
  assert.equal(p.versions.length, 1);
  assert.equal(p.first.id, '1');
  assert.equal(p.current.id, '1');
});

test('re-uploads of the same file name are versions, oldest first regardless of input order', () => {
  const p = primaryPrd(epic(att(3, 'prd.md', '2026-10-03T10:00:00.000+0800'), att(1, 'PRD.md', '2026-09-01T10:00:00.000+0800'), att(2, 'prd.md', '2026-09-15T10:00:00.000+0800')));
  assert.deepEqual(p.versions.map((v) => v.id), ['1', '2', '3']);
  assert.equal(p.first.id, '1');
  assert.equal(p.current.id, '3');
});

test('primary PRD is the file name uploaded first; other markdown files are ignored', () => {
  const p = primaryPrd(epic(att(1, 'prd.md', '2026-09-01T10:00:00.000+0800'), att(2, 'notes.md', '2026-09-02T10:00:00.000+0800')));
  assert.equal(p.filename, 'prd.md');
  assert.equal(p.versions.length, 1);
});

test('PRD_ATTACHMENT_PATTERN narrows which files count', () => {
  const e = epic(att(1, 'notes.md', '2026-09-01T10:00:00.000+0800'), att(2, 'PRD-v1.md', '2026-09-02T10:00:00.000+0800'));
  assert.equal(primaryPrd(e, 'prd.*\\.md$').first.id, '2');
  assert.equal(primaryPrd(e, '^nothing$'), null);
});

test('window is decided by the first upload', () => {
  const early = primaryPrd(epic(att(1, 'prd.md', '2026-07-01T10:00:00.000+0800'), att(2, 'prd.md', '2026-09-01T10:00:00.000+0800')));
  const inside = primaryPrd(epic(att(3, 'prd.md', '2026-09-01T10:00:00.000+0800')));
  assert.equal(inWindow(early, range), false);
  assert.equal(inWindow(inside, range), true);
  assert.equal(inWindow(null, range), false);
});

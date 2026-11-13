// PRDs stored as markdown attachments on Jira epics. Pure helpers (no I/O) so they are easy to unit test.
import { lc, parseDate } from './util.js';

/** Default filter for the PRD attachment: any markdown file. Narrow with PRD_ATTACHMENT_PATTERN, e.g. "prd.*\\.md$". */
export const DEFAULT_PATTERN = '\\.md$';

/**
 * The PRD for an epic, from its attachments (Jira keeps every upload as its own attachment, so re-uploading a file
 * with the same name is how a new "version" appears). Matching attachments are grouped by file name; the primary PRD
 * is the file name that was uploaded first. Returns null when the epic has no matching attachment.
 *   { filename, versions: [{id, filename, created: Date}] sorted oldest -> newest, first, current }
 */
export function primaryPrd(issue, pattern = DEFAULT_PATTERN) {
  const re = new RegExp(pattern, 'i');
  const matching = (issue.fields?.attachment ?? [])
    .filter((a) => re.test(a.filename ?? ''))
    .map((a) => ({ id: String(a.id), filename: a.filename, created: parseDate(a.created) }))
    .filter((a) => a.created)
    .sort((a, b) => a.created - b.created);
  if (!matching.length) return null;
  const name = lc(matching[0].filename);
  const versions = matching.filter((a) => lc(a.filename) === name);
  return { filename: matching[0].filename, versions, first: versions[0], current: versions.at(-1) };
}

/** True when the PRD was first uploaded inside the report window. */
export const inWindow = (prd, range) => !!prd && prd.first.created >= range.from && prd.first.created <= range.to;

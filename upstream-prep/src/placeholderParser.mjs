/**
 * AutoCite upstream exploration: side-effect-free placeholder scanning.
 * No Zotero APIs or Word document fields are touched here.
 *
 * SPDX-License-Identifier: MIT
 */

const ZOTERO_KEY = /^[A-Z0-9]{8}$/;
const DOI = /^10\.\d{4,9}\/[^\s\[\]<>]{1,200}$/i;
const ALIAS = /^\d{1,10}$/;
const OPEN = /\[\[([^\]\r\n]{0,300})\]\]/g;
const MAX_DOCUMENT_LENGTH = 20_000_000;
const MAX_MARKERS = 10_000;

function invalid(raw, message) {
  return { kind: 'invalid', error: message, raw };
}

export function parsePlaceholder(rawMarker) {
  if (typeof rawMarker !== 'string' || !rawMarker.startsWith('[[') || !rawMarker.endsWith(']]')) {
    return invalid(rawMarker, 'Expected a complete [[...]] marker');
  }
  const body = rawMarker.slice(2, -2).trim();
  const separator = body.indexOf(':');
  const prefix = separator < 0 ? '' : body.slice(0, separator).trim().toUpperCase();
  const value = separator < 0 ? '' : body.slice(separator + 1).trim();
  if (prefix === 'Z') {
    if (!ALIAS.test(value)) return invalid(rawMarker, 'Alias must contain 1–10 decimal digits');
    // Leading zeroes are meaningful in a given catalog: do not turn into Number.
    return { kind: 'alias', value, canonical: `[[Z:${value}]]` };
  }
  if (prefix === 'ZDOI') {
    // Explicit DOI markers only; free-text surname/year is deliberately unsupported.
    const doi = value.replace(/^https?:\/\/(?:dx\.)?doi\.org\//i, '').toLowerCase();
    if (!DOI.test(doi)) return invalid(rawMarker, 'Not a valid DOI marker');
    return { kind: 'doi', value: doi, canonical: `[[ZDOI:${doi}]]` };
  }
  if (prefix === 'ZOTERO') {
    const match = value.match(/^(user|group:\d+)\/([a-z0-9]{8})$/i);
    if (!match || !ZOTERO_KEY.test(match[2].toUpperCase())) {
      return invalid(rawMarker, 'Use user/ITEMKEY or group:ID/ITEMKEY');
    }
    const library = match[1].toLowerCase();
    const key = match[2].toUpperCase();
    return { kind: 'zotero', value: { library, key }, canonical: `[[ZOTERO:${library}/${key}]]` };
  }
  return null; // Other [[...]] expressions belong to the document, not AutoCite.
}

/** Return recognized markers, including invalid AutoCite-prefixed markers, with offsets. */
export function scanCitationMarkers(text) {
  if (typeof text !== 'string') throw new TypeError('Document text must be a string');
  if (text.length > MAX_DOCUMENT_LENGTH) throw new RangeError('Document text exceeds scanner limit');
  const matches = [];
  for (const match of text.matchAll(OPEN)) {
    const parsed = parsePlaceholder(match[0]);
    if (!parsed) continue;
    if (matches.length >= MAX_MARKERS) throw new RangeError('Too many AutoCite markers');
    matches.push({ raw: match[0], start: match.index, end: match.index + match[0].length, ...parsed });
  }
  return matches;
}

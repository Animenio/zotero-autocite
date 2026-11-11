/**
 * AutoCite upstream exploration: deterministic, read-only lookup planning.
 * The result is an edit plan, NOT Word fields. The Zotero integration layer
 * must own document edits, undo transactions, and citation/bibliography update.
 * SPDX-License-Identifier: MIT
 */
import { scanCitationMarkers } from './placeholderParser.mjs';

function referenceId(marker) {
  if (marker.kind === 'zotero') return `zotero:${marker.value.library}/${marker.value.key}`;
  return `${marker.kind}:${marker.value}`;
}

function validateItem(item) {
  if (!item || typeof item !== 'object') return null;
  if (!/^[A-Z0-9]{8}$/.test(String(item.itemKey || ''))) return null;
  if (!/^(user|group:\d+)$/.test(String(item.library || ''))) return null;
  return { library: item.library, itemKey: item.itemKey, title: String(item.title || ''), ...(Number.isSafeInteger(item.itemID) && item.itemID > 0 ? { itemID: item.itemID } : {}), ...(item.doi ? { doi: String(item.doi).toLowerCase().replace(/^https?:\/\/(?:dx\.)?doi\.org\//, '') } : {}) };
}

/**
 * Resolver interface, all async and read-only:
 *   resolveAlias(alias) / resolveDOI(doi) / resolveZoteroItem({library,key}).
 * Resolver should return: {status:'found', item:{library,itemKey,title}},
 * {status:'missing'}, {status:'ambiguous'} or {status:'error',message}.
 * Nothing is ever imported automatically by this module.
 */
export async function buildCitationPlan(text, resolver) {
  const markers = scanCitationMarkers(text);
  const cache = new Map();
  const occurrences = [];
  for (const marker of markers) {
    if (marker.kind === 'invalid') {
      occurrences.push({ ...marker, status: 'INVALID', reason: marker.error });
      continue;
    }
    const identity = referenceId(marker);
    if (!cache.has(identity)) {
      let result;
      try {
        if (marker.kind === 'alias') result = await resolver.resolveAlias(marker.value);
        else if (marker.kind === 'doi') result = await resolver.resolveDOI(marker.value);
        else result = await resolver.resolveZoteroItem(marker.value);
      } catch (error) {
        result = { status: 'error', message: String(error?.message || error) };
      }
      if (result?.status === 'found') {
        const item = validateItem(result.item);
        if (!item) {
          result = { status: 'error', message: 'Invalid resolved Zotero item identity' };
        }
        else if (marker.kind === 'zotero' && (item.library !== marker.value.library || item.itemKey !== marker.value.key)) {
          result = { status: 'error', message: 'Returned Zotero item does not match requested library and key' };
        }
        else if (marker.kind === 'doi' && item.doi !== marker.value) {
          result = { status: 'error', message: 'Returned Zotero item DOI does not match requested DOI' };
        }
        else {
          result = { status: 'found', item };
        }
      }
      if (!['found', 'missing', 'ambiguous', 'error'].includes(result?.status)) {
        result = { status: 'error', message: 'Resolver returned an unknown status' };
      }
      cache.set(identity, result);
    }
    const result = cache.get(identity);
    const status = { found: 'RESOLVED', missing: 'MISSING', ambiguous: 'AMBIGUOUS', error: 'ERROR' }[result.status];
    occurrences.push({ ...marker, status, ...(result.item ? { item: result.item } : {}), ...(result.message ? { reason: result.message.slice(0, 400) } : {}) });
  }
  const replacements = occurrences.filter(x => x.status === 'RESOLVED').sort((a, b) => b.start - a.start);
  const uniqueSources = [...new Map(replacements.map(x => [`${x.item.library}/${x.item.itemKey}`, x.item])).values()];
  const counts = Object.fromEntries(['RESOLVED', 'MISSING', 'AMBIGUOUS', 'ERROR', 'INVALID'].map(k => [k, occurrences.filter(x => x.status === k).length]));
  return { occurrences, replacements, uniqueSources, counts, hasErrors: occurrences.some(x => x.status !== 'RESOLVED') };
}

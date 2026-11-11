/**
 * Experimental integration boundary; no COM or OOXML code is supplied here.
 * Intended for a future adapter implemented in the official Zotero Word layer.
 * SPDX-License-Identifier: MIT
 */
export async function applyNativeConversion(plan, adapter, { allowPartial = false } = {}) {
  if (!plan || !Array.isArray(plan.replacements) || !Array.isArray(plan.occurrences)) {
    throw new TypeError('A valid citation plan is required');
  }
  if (!allowPartial && plan.hasErrors) {
    return { applied: 0, status: 'BLOCKED_UNRESOLVED', unresolved: plan.occurrences.filter(x => x.status !== 'RESOLVED') };
  }
  if (!plan.replacements.length) return { applied: 0, status: 'NO_CHANGES' };
  const required = ['beginUndoTransaction', 'replaceMarkerWithCitationField', 'commitUndoTransaction', 'rollbackUndoTransaction'];
  for (const method of required) {
    if (typeof adapter?.[method] !== 'function') throw new TypeError(`Native adapter missing ${method}`);
  }
  let transaction;
  try {
    transaction = await adapter.beginUndoTransaction();
    for (const marker of plan.replacements) {
      // Reverse order is deliberate: earlier offsets remain stable after replacement.
      await adapter.replaceMarkerWithCitationField({
        start: marker.start, end: marker.end, originalText: marker.raw,
        library: marker.item.library, itemKey: marker.item.itemKey,
      });
    }
    await adapter.commitUndoTransaction(transaction);
    return { applied: plan.replacements.length, status: 'APPLIED_PENDING_ZOTERO_REFRESH' };
  } catch(error) {
    if (transaction !== undefined) {
      try { await adapter.rollbackUndoTransaction(transaction); }
      catch(rollbackError) {
        throw new AggregateError([error, rollbackError], 'Conversion and rollback failed; inspect the document');
      }
    }
    throw error;
  }
}

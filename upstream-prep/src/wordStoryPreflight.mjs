"use strict";

/**
 * Validate a Word document snapshot before any native field insertion.
 *
 * All offsets are JavaScript UTF-16 code units relative to snapshot.text.
 * The native Windows adapter must recheck the same text immediately before
 * insertion and create a verified, independent backup before applying edits.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

/**
 * @param {Object} snapshot - Verified main story metadata from Word.
 * @param {Object} batch - Output of prepareNativeCitationBatch().
 * @returns {Object} Safe absolute Word range plan or a blocking reason.
 */
export function preflightWordStory(snapshot, batch) {
	let block = reason => ({ status: 'blocked', reason, changes: [] });

	if (!snapshot || typeof snapshot.text !== 'string' || !batch) {
		throw new TypeError('Expected a Word story snapshot and native citation batch');
	}
	if (batch.status === 'blocked') {
		return block('References were not fully resolved');
	}
	if (batch.status !== 'ready' || !Array.isArray(batch.changes)
		|| !batch.changes.length) {
		return { status: 'empty', changes: [] };
	}
	if (snapshot.storyType !== 'main') {
		return block('Only the main document text story is supported');
	}
	if (!snapshot.isSaved || snapshot.readOnly || snapshot.trackRevisions) {
		return block('Word document must be saved, editable and without Track Changes');
	}
	if (!Number.isSafeInteger(snapshot.storyStart) || snapshot.storyStart < 0) {
		return block('Invalid Word story start offset');
	}
	if (!Array.isArray(snapshot.fieldRanges)
		|| !snapshot.fieldRanges.every(x => Number.isSafeInteger(x.start)
			&& Number.isSafeInteger(x.end) && x.start >= 0 && x.end > x.start)) {
		return block('Word field ranges are missing or invalid');
	}

	let output = [];
	let lastStart = snapshot.text.length + 1;
	for (let change of batch.changes) {
		if (!Number.isSafeInteger(change.start)
			|| !Number.isSafeInteger(change.end)
			|| change.start < 0 || change.end <= change.start
			|| change.end > snapshot.text.length
			|| change.end > lastStart) {
			return block('Invalid or overlapping replacement offsets');
		}
		if (snapshot.text.slice(change.start, change.end) !== change.raw) {
			return block('Text has changed since the citation plan was built');
		}
		if (snapshot.fieldRanges.some(field =>
			change.start < field.end && field.start < change.end)) {
			return block('A replacement overlaps an existing Word field');
		}
		if (!Array.isArray(change.citationItems) || change.citationItems.length !== 1
			|| !Number.isSafeInteger(change.citationItems[0].id)
			|| change.citationItems[0].id <= 0) {
			return block('Invalid native Zotero citation item ID');
		}

		let start = snapshot.storyStart + change.start;
		let end = snapshot.storyStart + change.end;
		if (!Number.isSafeInteger(start) || !Number.isSafeInteger(end)) {
			return block('Word absolute offset exceeds supported range');
		}
		output.push({
			start, end, expectedText: change.raw,
			citationItems: change.citationItems.map(item => ({ id: item.id }))
		});
		lastStart = change.start;
	}
	return { status: 'ready', changes: output };
}

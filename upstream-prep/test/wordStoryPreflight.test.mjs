"use strict";

/** SPDX-License-Identifier: AGPL-3.0-or-later */

import test from 'node:test';
import assert from 'node:assert/strict';
import { preflightWordStory } from '../src/wordStoryPreflight.mjs';

const MARKER = '[[ZOTERO:user/HJVM9AMK]]';

function fixture(text = 'A ' + MARKER + ' B') {
	let start = text.indexOf(MARKER);
	return {
		snapshot: {
			text, storyType: 'main', storyStart: 80,
			isSaved: true, readOnly: false, trackRevisions: false,
			fieldRanges: []
		},
		batch: {
			status: 'ready',
			changes: [{
				start, end: start + MARKER.length, raw: MARKER,
				citationItems: [{ id: 4242 }]
			}]
		}
	};
}

test('maps validated relative text offsets to absolute Word story ranges', () => {
	let { snapshot, batch } = fixture();
	let result = preflightWordStory(snapshot, batch);
	assert.equal(result.status, 'ready');
	assert.equal(result.changes[0].start, 82);
	assert.equal(result.changes[0].end, 82 + MARKER.length);
	assert.deepEqual(result.changes[0].citationItems, [{ id: 4242 }]);
});

test('rejects a Word field overlapping the marker', () => {
	let { snapshot, batch } = fixture();
	snapshot.fieldRanges = [{ start: 3, end: 8 }];
	let result = preflightWordStory(snapshot, batch);
	assert.equal(result.status, 'blocked');
	assert.equal(result.changes.length, 0);
});

test('allows Word fields elsewhere in the same document', () => {
	let { snapshot, batch } = fixture();
	snapshot.fieldRanges = [{ start: 0, end: 1 }];
	assert.equal(preflightWordStory(snapshot, batch).status, 'ready');
});

test('rejects changed marker text even when length is unchanged', () => {
	let { snapshot, batch } = fixture();
	snapshot.text = snapshot.text.replace('HJVM9AMK', 'ABCDEFGH');
	assert.equal(preflightWordStory(snapshot, batch).status, 'blocked');
});

test('rejects unsaved documents, read-only documents and tracked changes', () => {
	for (let property of ['isSaved', 'readOnly', 'trackRevisions']) {
		let { snapshot, batch } = fixture();
		snapshot[property] = property !== 'isSaved';
		assert.equal(preflightWordStory(snapshot, batch).status, 'blocked');
	}
});

test('supports only the main story; headings and footnotes need separate adapters', () => {
	let { snapshot, batch } = fixture();
	snapshot.storyType = 'footnote';
	assert.equal(preflightWordStory(snapshot, batch).status, 'blocked');
});

test('rejects missing field boundaries rather than silently editing', () => {
	let { snapshot, batch } = fixture();
	delete snapshot.fieldRanges;
	assert.equal(preflightWordStory(snapshot, batch).status, 'blocked');
});

test('refuses invalid or overlapping batched ranges', () => {
	let { snapshot, batch } = fixture(MARKER + ' ' + MARKER);
	batch.changes = [
		{ start: MARKER.length + 1, end: MARKER.length * 2 + 1,
			raw: MARKER, citationItems: [{ id: 4242 }] },
		{ start: 1, end: 1 + MARKER.length, raw: MARKER,
			citationItems: [{ id: 4242 }] }
	];
	assert.equal(preflightWordStory(snapshot, batch).status, 'blocked');
});

test('supports two distinct markers in reverse order', () => {
	let { snapshot, batch } = fixture(MARKER + ' ' + MARKER);
	batch.changes = [
		{ start: MARKER.length + 1, end: MARKER.length * 2 + 1,
			raw: MARKER, citationItems: [{ id: 4242 }] },
		{ start: 0, end: MARKER.length, raw: MARKER,
			citationItems: [{ id: 4242 }] }
	];
	let result = preflightWordStory(snapshot, batch);
	assert.equal(result.status, 'ready');
	assert.equal(result.changes.length, 2);
	assert.ok(result.changes[0].start > result.changes[1].start);
});

test('does not emit changes for a blocked citation batch', () => {
	let { snapshot, batch } = fixture();
	batch.status = 'blocked';
	assert.equal(preflightWordStory(snapshot, batch).changes.length, 0);
});

test('rejects invalid native Zotero IDs before requesting a Word edit', () => {
	let { snapshot, batch } = fixture();
	batch.changes[0].citationItems[0].id = 0;
	assert.equal(preflightWordStory(snapshot, batch).status, 'blocked');
});

test('rejects a story offset that would exceed safe integer precision', () => {
	let { snapshot, batch } = fixture();
	snapshot.storyStart = Number.MAX_SAFE_INTEGER;
	assert.equal(preflightWordStory(snapshot, batch).status, 'blocked');
});

test('does not mutate Word snapshots or edit plans', () => {
	let { snapshot, batch } = fixture();
	let beforeSnapshot = JSON.stringify(snapshot);
	let beforeBatch = JSON.stringify(batch);
	preflightWordStory(snapshot, batch);
	assert.equal(JSON.stringify(snapshot), beforeSnapshot);
	assert.equal(JSON.stringify(batch), beforeBatch);
});

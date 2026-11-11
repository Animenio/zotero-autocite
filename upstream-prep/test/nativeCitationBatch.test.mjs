"use strict";

/** SPDX-License-Identifier: AGPL-3.0-or-later */

import test from 'node:test';
import assert from 'node:assert/strict';
import { prepareNativeCitationBatch } from '../src/nativeCitationBatch.mjs';

const KEY = 'HJVM9AMK';
const PERSONAL = '[[ZOTERO:user/' + KEY + ']]';
const GROUP = '[[ZOTERO:group:123/' + KEY + ']]';
const MISSING = '[[ZOTERO:group:124/' + KEY + ']]';

function runtime() {
	let lookups = [];
	return {
		lookups,
		zotero: {
			Libraries: { userLibraryID: 1 },
			Groups: { getLibraryIDFromGroupID: id => id === 123 ? 5 : false },
			Items: {
				async getByLibraryAndKeyAsync(libraryID, key) {
					lookups.push([libraryID, key]);
					return {
						id: libraryID === 1 ? 4242 : 5252,
						libraryID, key, deleted: false,
						isRegularItem: () => true,
						getDisplayTitle: () => 'A valid study',
						getField: () => ''
					};
				}
			}
		}
	};
}

test('returns Zotero-native citation item ID, not a handcrafted field', async () => {
	let { zotero } = runtime();
	let batch = await prepareNativeCitationBatch(PERSONAL, zotero);
	assert.equal(batch.status, 'ready');
	assert.deepEqual(batch.changes[0].citationItems, [{ id: 4242 }]);
	assert.equal(batch.changes[0].start, 0);
	assert.equal(batch.changes[0].end, PERSONAL.length);
	assert.equal(Object.hasOwn(batch.changes[0], 'fieldCode'), false);
});

test('keeps positional offsets and processes repeats from right to left', async () => {
	let { zotero, lookups } = runtime();
	let input = PERSONAL + ' and ' + PERSONAL;
	let batch = await prepareNativeCitationBatch(input, zotero);
	assert.equal(batch.changes.length, 2);
	assert.ok(batch.changes[0].start > batch.changes[1].start);
	assert.equal(batch.changes[0].raw, PERSONAL);
	assert.deepEqual(lookups, [[1, KEY]]);
});

test('group and user item IDs are different, even for identical keys', async () => {
	let { zotero } = runtime();
	let batch = await prepareNativeCitationBatch(PERSONAL + ' ' + GROUP, zotero);
	assert.equal(batch.status, 'ready');
	assert.deepEqual(batch.changes.map(x => x.citationItems[0].id), [5252, 4242]);
});

test('the entire batch is blocked by an inaccessible group', async () => {
	let { zotero } = runtime();
	let batch = await prepareNativeCitationBatch(PERSONAL + ' ' + MISSING, zotero);
	assert.equal(batch.status, 'blocked');
	assert.deepEqual(batch.changes, []);
	assert.equal(batch.problems[0].status, 'MISSING');
});

test('the entire batch is blocked by a local catalog alias', async () => {
	let { zotero } = runtime();
	let batch = await prepareNativeCitationBatch(PERSONAL + ' [[Z:06937]]', zotero);
	assert.equal(batch.status, 'blocked');
	assert.deepEqual(batch.changes, []);
	assert.equal(batch.problems[0].status, 'ERROR');
});

test('DOI markers are out of scope and cannot trigger partial conversions', async () => {
	let { zotero } = runtime();
	let batch = await prepareNativeCitationBatch(
		PERSONAL + ' [[ZDOI:10.5555/example]]', zotero
	);
	assert.equal(batch.status, 'blocked');
	assert.equal(batch.changes.length, 0);
});

test('invalid Zotero item keys do not produce citations', async () => {
	let { zotero, lookups } = runtime();
	let batch = await prepareNativeCitationBatch('[[ZOTERO:user/00000000]]', zotero);
	assert.equal(batch.status, 'blocked');
	assert.equal(lookups.length, 0);
});

test('returns empty on a document without citations', async () => {
	let { zotero } = runtime();
	let batch = await prepareNativeCitationBatch('No markers here.', zotero);
	assert.equal(batch.status, 'empty');
	assert.deepEqual(batch.changes, []);
});

test('offsets are JavaScript UTF-16 units for future Word range mapping', async () => {
	let { zotero } = runtime();
	let batch = await prepareNativeCitationBatch('😀 ' + PERSONAL, zotero);
	assert.equal(batch.changes[0].start, 3);
});

test('does not modify the source snapshot', async () => {
	let { zotero } = runtime();
	let input = 'Before ' + PERSONAL + ' after';
	await prepareNativeCitationBatch(input, zotero);
	assert.equal(input, 'Before ' + PERSONAL + ' after');
});

test('refuses invalid Zotero database IDs even with a valid library/key', async () => {
	let { zotero } = runtime();
	zotero.Items.getByLibraryAndKeyAsync = async (libraryID, key) => ({
		id: -20, libraryID, key,
		isRegularItem: () => true,
		getDisplayTitle: () => 'Study', getField: () => ''
	});
	let batch = await prepareNativeCitationBatch(PERSONAL, zotero);
	assert.equal(batch.status, 'blocked');
	assert.deepEqual(batch.changes, []);
});

test('lookup errors never produce partial editing instructions', async () => {
	let { zotero } = runtime();
	zotero.Items.getByLibraryAndKeyAsync = async () => {
		throw new Error('Database error');
	};
	let batch = await prepareNativeCitationBatch(PERSONAL, zotero);
	assert.equal(batch.status, 'blocked');
	assert.equal(batch.changes.length, 0);
});

test('unknown bracket tokens are not treated as Zotero citations', async () => {
	let { zotero } = runtime();
	let batch = await prepareNativeCitationBatch('[[UNRELATED:ABCDEFGH]]', zotero);
	assert.equal(batch.status, 'empty');
});

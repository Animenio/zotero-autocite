"use strict";

/** SPDX-License-Identifier: AGPL-3.0-or-later */
import test from 'node:test';
import assert from 'node:assert/strict';
import { createZoteroNativeResolver } from '../src/zoteroNativeLookup.mjs';
import { buildCitationPlan } from '../src/resolutionPlanner.mjs';

const KEY = 'HJVM9AMK';

function fakeZotero() {
	let requests = [];
	let zotero = {
		Libraries: { userLibraryID: 1 },
		Groups: { getLibraryIDFromGroupID: groupID => groupID === 123 ? 5 : false },
		Items: {
			async getByLibraryAndKeyAsync(libraryID, key) {
				requests.push([libraryID, key]);
				return {
					libraryID,
					key,
					deleted: false,
					isRegularItem: () => true,
					getDisplayTitle: () => 'The future of employment',
					getField: name => name === 'DOI'
						? '10.1016/j.techfore.2016.08.019' : ''
				};
			}
		}
	};
	return { zotero, requests };
}

test('resolves a personal item using the exact Zotero library ID', async () => {
	let { zotero, requests } = fakeZotero();
	let resolver = createZoteroNativeResolver(zotero);
	let result = await resolver.resolveZoteroItem({ library: 'user', key: KEY });
	assert.equal(result.status, 'found');
	assert.deepEqual(requests, [[1, KEY]]);
	assert.equal(result.item.library, 'user');
});

test('resolves a group item without falling back to personal library', async () => {
	let { zotero, requests } = fakeZotero();
	let resolver = createZoteroNativeResolver(zotero);
	let result = await resolver.resolveZoteroItem({ library: 'group:123', key: KEY });
	assert.equal(result.status, 'found');
	assert.deepEqual(requests, [[5, KEY]]);
	assert.equal(result.item.library, 'group:123');
});

test('rejects an inaccessible group without consulting another library', async () => {
	let { zotero, requests } = fakeZotero();
	let resolver = createZoteroNativeResolver(zotero);
	let result = await resolver.resolveZoteroItem({ library: 'group:124', key: KEY });
	assert.equal(result.status, 'missing');
	assert.deepEqual(requests, []);
});

test('rejects invalid group scope and item key', async () => {
	let { zotero } = fakeZotero();
	let resolver = createZoteroNativeResolver(zotero);
	assert.equal((await resolver.resolveZoteroItem({
		library: 'group:00123', key: KEY
	})).status, 'error');
	assert.equal((await resolver.resolveZoteroItem({
		library: 'user', key: '00000000'
	})).status, 'error');
});

test('does not allow an item returned from a different library', async () => {
	let { zotero } = fakeZotero();
	zotero.Items.getByLibraryAndKeyAsync = async (_, key) => ({
		libraryID: 999, key, isRegularItem: () => true
	});
	let result = await createZoteroNativeResolver(zotero).resolveZoteroItem({
		library: 'user', key: KEY
	});
	assert.equal(result.status, 'error');
});

test('does not allow a mismatched item key', async () => {
	let { zotero } = fakeZotero();
	zotero.Items.getByLibraryAndKeyAsync = async libraryID => ({
		libraryID, key: 'ABCDEFGH', isRegularItem: () => true
	});
	let result = await createZoteroNativeResolver(zotero).resolveZoteroItem({
		library: 'user', key: KEY
	});
	assert.equal(result.status, 'error');
});

test('rejects deleted, nonregular and feed items', async () => {
	for (let mutation of [
		item => { item.deleted = true; },
		item => { item.isRegularItem = () => false; },
		item => { item.isFeedItem = true; }
	]) {
		let { zotero } = fakeZotero();
		let original = zotero.Items.getByLibraryAndKeyAsync;
		zotero.Items.getByLibraryAndKeyAsync = async (libraryID, key) => {
			let item = await original(libraryID, key);
			mutation(item);
			return item;
		};
		let result = await createZoteroNativeResolver(zotero).resolveZoteroItem({
			library: 'user', key: KEY
		});
		assert.equal(result.status, 'error');
	}
});

test('returns missing for an unknown item, without inventing metadata', async () => {
	let { zotero } = fakeZotero();
	zotero.Items.getByLibraryAndKeyAsync = async () => false;
	let result = await createZoteroNativeResolver(zotero).resolveZoteroItem({
		library: 'user', key: KEY
	});
	assert.deepEqual(result, { status: 'missing' });
});

test('lookup exceptions do not cause fallback or creation', async () => {
	let { zotero } = fakeZotero();
	zotero.Items.getByLibraryAndKeyAsync = async () => {
		throw new Error('Zotero database unavailable');
	};
	let result = await createZoteroNativeResolver(zotero).resolveZoteroItem({
		library: 'user', key: KEY
	});
	assert.equal(result.status, 'error');
});

test('legacy aliases and external DOI lookup are intentionally unsupported', async () => {
	let { zotero } = fakeZotero();
	let resolver = createZoteroNativeResolver(zotero);
	assert.equal((await resolver.resolveAlias('06937')).status, 'error');
	assert.equal((await resolver.resolveDOI('10.1234/example')).status, 'error');
});

test('integrates with the planner and caches repeated exact references', async () => {
	let { zotero, requests } = fakeZotero();
	let resolver = createZoteroNativeResolver(zotero);
	let text = '[[ZOTERO:user/' + KEY + ']] and [[ZOTERO:user/' + KEY + ']]';
	let plan = await buildCitationPlan(text, resolver);
	assert.equal(plan.hasErrors, false);
	assert.equal(plan.replacements.length, 2);
	assert.equal(plan.uniqueSources.length, 1);
	assert.deepEqual(requests, [[1, KEY]]);
	assert.ok(plan.replacements[0].start > plan.replacements[1].start);
});

test('one inaccessible reference blocks a mixed plan by default', async () => {
	let { zotero } = fakeZotero();
	let resolver = createZoteroNativeResolver(zotero);
	let text = '[[ZOTERO:user/' + KEY + ']] [[ZOTERO:group:124/' + KEY + ']]';
	let plan = await buildCitationPlan(text, resolver);
	assert.equal(plan.hasErrors, true);
	assert.equal(plan.counts.RESOLVED, 1);
	assert.equal(plan.counts.MISSING, 1);
});

test('same key in group and user library resolves to different identities', async () => {
	let { zotero, requests } = fakeZotero();
	let resolver = createZoteroNativeResolver(zotero);
	let text = '[[ZOTERO:user/' + KEY + ']] [[ZOTERO:group:123/' + KEY + ']]';
	let plan = await buildCitationPlan(text, resolver);
	assert.equal(plan.hasErrors, false);
	assert.equal(plan.uniqueSources.length, 2);
	assert.deepEqual(requests, [[1, KEY], [5, KEY]]);
});

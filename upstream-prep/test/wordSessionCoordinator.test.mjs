"use strict";

/** SPDX-License-Identifier: AGPL-3.0-or-later */

import test from 'node:test';
import assert from 'node:assert/strict';
import { convertNativeWordPlaceholders } from '../src/wordSessionCoordinator.mjs';

const MARKER = '[[ZOTERO:user/HJVM9AMK]]';

function fixture(text = MARKER) {
	let calls = [];
	let rawField = {
		id: 'new-field',
		async equals(other) { return this.id === other.id; }
	};
	let context = {
		zotero: {
			Libraries: { userLibraryID: 1 },
			Groups: { getLibraryIDFromGroupID: () => false },
			Items: {
				async getByLibraryAndKeyAsync(libraryID, key) {
					calls.push('lookup');
					return {
						id: 4242, libraryID, key, deleted: false,
						isRegularItem: () => true,
						getDisplayTitle: () => 'Valid source',
						getField: () => ''
					};
				}
			}
		},
		integration: {
			CitationField: class {
				constructor(field) { this.field = field; }
				async getNoteIndex() { return 0; }
			},
			Citation: class {
				constructor(field, data) {
					this.field = field;
					this.citationItems = data.citationItems;
				}
			}
		},
		session: {
			async getFields() {
				calls.push('fields');
				return [rawField];
			},
			async updateFromDocument() { calls.push('sync'); },
			async addCitation(index, noteIndex, citation) {
				calls.push('register');
				assert.deepEqual(citation.citationItems, [{ id: 4242 }]);
			},
			async updateDocument() { calls.push('refresh'); }
		},
		word: {
			async readMainStorySnapshot() {
				calls.push('scan');
				return {
					text, storyType: 'main', storyStart: 0,
					isSaved: true, readOnly: false, trackRevisions: false,
					fieldRanges: []
				};
			},
			async verifyStorySnapshot() { calls.push('verify'); return true; },
			async createVerifiedBackup() {
				calls.push('backup');
				return { verified: true, path: 'sample_BACKUP.docx' };
			},
			async beginUndoTransaction() { calls.push('begin'); return { id: 1 }; },
			async replaceRangeWithTemporaryField(range) {
				calls.push('replace');
				assert.equal(range.expectedText, MARKER);
				return rawField;
			},
			async commitUndoTransaction() { calls.push('commit'); return true; },
			async rollbackUndoTransaction() { calls.push('rollback'); return true; }
		}
	};
	return { context, calls };
}

test('performs backup then native field insertion and session update in order', async () => {
	let { context, calls } = fixture();
	let result = await convertNativeWordPlaceholders(context);
	assert.deepEqual(result, {
		status: 'inserted_unsaved', applied: 1, backupPath: 'sample_BACKUP.docx'
	});
	assert.deepEqual(calls, [
		'scan', 'lookup', 'verify', 'backup', 'begin', 'replace',
		'fields', 'sync', 'register', 'refresh', 'commit'
	]);
});

test('does not write or back up a document with no markers', async () => {
	let { context, calls } = fixture('No references');
	let result = await convertNativeWordPlaceholders(context);
	assert.equal(result.status, 'empty');
	assert.deepEqual(calls, ['scan']);
});

test('unresolved references block the entire conversion before backup', async () => {
	let { context, calls } = fixture(MARKER + ' [[Z:06937]]');
	let result = await convertNativeWordPlaceholders(context);
	assert.equal(result.status, 'blocked');
	assert.equal(result.applied, 0);
	assert.ok(!calls.includes('backup'));
	assert.ok(!calls.includes('replace'));
});

test('snapshot changes prevent backup and all Word edits', async () => {
	let { context, calls } = fixture();
	context.word.verifyStorySnapshot = async () => false;
	let result = await convertNativeWordPlaceholders(context);
	assert.equal(result.status, 'blocked');
	assert.ok(!calls.includes('backup'));
});

test('backup not verified stops before starting an undo transaction', async () => {
	let { context, calls } = fixture();
	context.word.createVerifiedBackup = async () => ({ verified: false, path: 'bad.docx' });
	await assert.rejects(
		convertNativeWordPlaceholders(context), /backup was not verified/
	);
	assert.ok(!calls.includes('begin'));
	assert.ok(!calls.includes('replace'));
});

test('native field insertion failure triggers rollback', async () => {
	let { context, calls } = fixture();
	context.word.replaceRangeWithTemporaryField = async () => {
		calls.push('replace');
		throw new Error('OLE insert failed');
	};
	await assert.rejects(
		convertNativeWordPlaceholders(context), /OLE insert failed/
	);
	assert.ok(calls.includes('rollback'));
	assert.ok(!calls.includes('refresh'));
});

test('failure during Zotero refresh triggers native rollback', async () => {
	let { context, calls } = fixture();
	context.session.updateDocument = async () => {
		calls.push('refresh');
		throw new Error('Citeproc error');
	};
	await assert.rejects(
		convertNativeWordPlaceholders(context), /Citeproc error/
	);
	assert.equal(calls.at(-1), 'rollback');
});

test('rollback failure is reported rather than hidden', async () => {
	let { context } = fixture();
	context.word.replaceRangeWithTemporaryField = async () => {
		throw new Error('Primary error');
	};
	context.word.rollbackUndoTransaction = async () => false;
	await assert.rejects(
		convertNativeWordPlaceholders(context), AggregateError
	);
});

test('adapter missing rollback is rejected before any scans or edits', async () => {
	let { context, calls } = fixture();
	delete context.word.rollbackUndoTransaction;
	await assert.rejects(
		convertNativeWordPlaceholders(context), /missing rollbackUndoTransaction/
	);
	assert.deepEqual(calls, []);
});

test('tracked changes refuse any mutation', async () => {
	let { context, calls } = fixture();
	let scan = context.word.readMainStorySnapshot;
	context.word.readMainStorySnapshot = async () => {
		let result = await scan();
		result.trackRevisions = true;
		return result;
	};
	let result = await convertNativeWordPlaceholders(context);
	assert.equal(result.status, 'blocked');
	assert.ok(!calls.includes('backup'));
});

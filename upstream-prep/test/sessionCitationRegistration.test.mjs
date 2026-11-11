"use strict";

/** SPDX-License-Identifier: AGPL-3.0-or-later */

import test from 'node:test';
import assert from 'node:assert/strict';
import { registerNativeCitations } from '../src/sessionCitationRegistration.mjs';

class Field {
	constructor(id) {
		this.id = id;
	}
	async equals(other) {
		return this.id === other.id;
	}
}

class CitationField {
	constructor(rawField) {
		this.rawField = rawField;
	}
	async getNoteIndex() {
		return 0;
	}
}

class Citation {
	constructor(field, data, noteIndex) {
		this.field = field;
		this.citationItems = data.citationItems;
		this.properties = data.properties;
		this.noteIndex = noteIndex;
	}
}

function fixture() {
	let calls = [];
	let fields = [new Field('old'), new Field('new1'), new Field('new2')];
	let session = {
		getFields: async force => {
			calls.push(['getFields', force]);
			return fields;
		},
		updateFromDocument: async force => calls.push(['updateFromDocument', force]),
		addCitation: async (index, noteIndex, citation) => {
			calls.push(['addCitation', index, noteIndex, citation.citationItems]);
		},
		updateDocument: async (...args) => calls.push(['updateDocument', ...args])
	};
	return { calls, fields, session, integration: { CitationField, Citation } };
}

test('registers two new items via Zotero Session and triggers canonical update', async () => {
	let { calls, fields, session, integration } = fixture();
	let result = await registerNativeCitations(session, integration, [
		{ field: fields[1], itemID: 4242 },
		{ field: fields[2], itemID: 5252 }
	]);
	assert.deepEqual(result, { status: 'registered', registered: 2 });
	assert.deepEqual(calls, [
		['getFields', true],
		['updateFromDocument', false],
		['addCitation', 1, 0, [{ id: 4242 }]],
		['addCitation', 2, 0, [{ id: 5252 }]],
		['updateDocument', 0, false, false]
	]);
});

test('does not generate or pass manually serialized Zotero field codes', async () => {
	let { fields, session, integration } = fixture();
	let received = [];
	session.addCitation = async (_, __, citation) => received.push(citation);
	await registerNativeCitations(session, integration, [{ field: fields[1], itemID: 4242 }]);
	assert.equal(received.length, 1);
	assert.deepEqual(received[0].citationItems, [{ id: 4242 }]);
	assert.equal(Object.hasOwn(received[0], 'code'), false);
});

test('blocks a field missing from the document before session mutation', async () => {
	let { calls, session, integration } = fixture();
	await assert.rejects(
		registerNativeCitations(session, integration, [
			{ field: new Field('lost'), itemID: 4242 }
		]),
		/uniquely identified/
	);
	assert.deepEqual(calls, [['getFields', true]]);
});

test('blocks duplicate assignments to the same Word field', async () => {
	let { calls, fields, session, integration } = fixture();
	await assert.rejects(
		registerNativeCitations(session, integration, [
			{ field: fields[1], itemID: 4242 },
			{ field: fields[1], itemID: 5252 }
		]),
		/uniquely identified/
	);
	assert.deepEqual(calls, [['getFields', true]]);
});

test('invalid item ID is rejected before any session read or mutation', async () => {
	let { calls, fields, session, integration } = fixture();
	await assert.rejects(
		registerNativeCitations(session, integration, [{ field: fields[1], itemID: -1 }]),
		/Invalid Zotero item ID/
	);
	assert.deepEqual(calls, []);
});

test('does nothing when no field assignments were supplied', async () => {
	let { calls, session, integration } = fixture();
	let result = await registerNativeCitations(session, integration, []);
	assert.deepEqual(result, { status: 'empty', registered: 0 });
	assert.deepEqual(calls, []);
});

test('missing Session APIs fail before any changes', async () => {
	let { integration } = fixture();
	await assert.rejects(
		registerNativeCitations({ getFields: async () => [] }, integration, []),
		/Expected Zotero Integration session/
	);
});

test('errors from Zotero update propagate for caller-owned native rollback', async () => {
	let { fields, session, integration } = fixture();
	session.updateDocument = async () => { throw new Error('CSL update failed'); };
	await assert.rejects(
		registerNativeCitations(session, integration, [
			{ field: fields[1], itemID: 4242 }
		]),
		/CSL update failed/
	);
});

test('ambiguous field equality blocks registration', async () => {
	let { calls, session, integration } = fixture();
	session.getFields = async force => {
		calls.push(['getFields', force]);
		return [new Field('duplicate'), new Field('duplicate')];
	};
	await assert.rejects(
		registerNativeCitations(session, integration, [
			{ field: new Field('duplicate'), itemID: 4242 }
		]),
		/uniquely identified/
	);
	assert.deepEqual(calls, [['getFields', true]]);
});

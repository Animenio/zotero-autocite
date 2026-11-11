"use strict";

/**
 * Experimental bridge to the official Zotero.Integration.Session methods.
 *
 * This function runs ONLY after a future native Word adapter has inserted
 * complete temporary fields and supplied their exact field objects.
 * The caller must already own a Word backup/undo transaction and must roll
 * back both document and session state if any step fails.
 *
 * It does not generate OOXML or manually serialize CSL field JSON.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

/**
 * @param {Object} session - Zotero.Integration.Session
 * @param {Object} integration - Zotero.Integration namespace
 * @param {Object[]} assignments - { field: nativeField, itemID: number }
 * @returns {Promise<Object>} Registration result
 */
export async function registerNativeCitations(session, integration, assignments) {
	if (!session || typeof session.getFields !== 'function'
		|| typeof session.updateFromDocument !== 'function'
		|| typeof session.addCitation !== 'function'
		|| typeof session.updateDocument !== 'function'
		|| typeof integration?.CitationField !== 'function'
		|| typeof integration?.Citation !== 'function'
		|| !Array.isArray(assignments)) {
		throw new TypeError('Expected Zotero Integration session and native field assignments');
	}
	if (!assignments.length) {
		return { status: 'empty', registered: 0 };
	}
	if (assignments.some(x => !x || !x.field
		|| !Number.isSafeInteger(x.itemID) || x.itemID <= 0)) {
		throw new TypeError('Invalid Zotero item ID or Word field');
	}

	// Zotero owns the canonical document field ordering, including existing
	// citation and bibliography fields. Do not guess Word field indices.
	let fields = await session.getFields(true);
	let records = [];
	let used = new Set();
	for (let assignment of assignments) {
		let matches = [];
		for (let index = 0; index < fields.length; index++) {
			if (typeof fields[index].equals !== 'function') {
				throw new TypeError('Zotero native fields must expose equals()');
			}
			if (await fields[index].equals(assignment.field)) {
				matches.push(index);
			}
		}
		if (matches.length !== 1 || used.has(matches[0])) {
			throw new Error('Inserted Zotero field was not uniquely identified');
		}
		used.add(matches[0]);
		records.push({ field: fields[matches[0]], index: matches[0], itemID: assignment.itemID });
	}

	// Process the existing fields before registering new citations, so Zotero
	// preserves its session metadata and existing bibliography state.
	await session.updateFromDocument(false);

	for (let record of records) {
		let citationField = new integration.CitationField(record.field);
		let noteIndex = await citationField.getNoteIndex();
		let citation = new integration.Citation(citationField, {
			citationItems: [{ id: record.itemID }],
			properties: {}
		}, noteIndex);
		citation.fieldIndex = record.index;
		await session.addCitation(record.index, noteIndex, citation);
	}

	// Session.updateDocument formats citations and serializes CSL codes using
	// Zotero's own implementation. Never build ADDIN ZOTERO_ITEM JSON here.
	await session.updateDocument(0, false, false);
	return { status: 'registered', registered: records.length };
}

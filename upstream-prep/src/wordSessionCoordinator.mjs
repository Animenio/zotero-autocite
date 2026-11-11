"use strict";

/**
 * Experiment-only native Word / Zotero Session orchestration.
 *
 * This module describes a contract for the not-yet-implemented upstream C++
 * and JS/ctypes bridge. It is NOT connected to the Zotero Word ribbon.
 * A verified backup must exist before any edits. Word rollback is
 * best-effort and cannot guarantee crash recovery; retain the backup.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

import { prepareNativeCitationBatch } from './nativeCitationBatch.mjs';
import { preflightWordStory } from './wordStoryPreflight.mjs';
import { registerNativeCitations } from './sessionCitationRegistration.mjs';

/**
 * @param {Object} context - { zotero, session, integration, word }
 * @returns {Promise<Object>} Status and verified-backup information
 */
export async function convertNativeWordPlaceholders(context) {
	const required = [
		'readMainStorySnapshot',
		'verifyStorySnapshot',
		'createVerifiedBackup',
		'beginUndoTransaction',
		'replaceRangeWithTemporaryField',
		'commitUndoTransaction',
		'rollbackUndoTransaction'
	];
	const word = context?.word;
	for (let method of required) {
		if (typeof word?.[method] !== 'function') {
			throw new TypeError('Native Word adapter missing ' + method);
		}
	}
	if (!context.zotero || !context.session || !context.integration) {
		throw new TypeError('Zotero Session and Integration are required');
	}

	const snapshot = await word.readMainStorySnapshot();
	const batch = await prepareNativeCitationBatch(snapshot.text, context.zotero);
	const checked = preflightWordStory(snapshot, batch);
	if (checked.status !== 'ready') {
		return { status: checked.status, applied: 0, reason: checked.reason || '' };
	}

	// Revalidate with the native Word adapter immediately before creating a
	// backup. A stale story snapshot must never be applied.
	if (await word.verifyStorySnapshot(snapshot) !== true) {
		return { status: 'blocked', applied: 0, reason: 'Word document changed since scan' };
	}

	const backup = await word.createVerifiedBackup();
	if (!backup || backup.verified !== true || typeof backup.path !== 'string'
		|| !backup.path.trim()) {
		throw new Error('Word backup was not verified: refusing document mutation');
	}

	let transaction;
	try {
		transaction = await word.beginUndoTransaction();
		const assignments = [];
		for (let change of checked.changes) {
			const nativeField = await word.replaceRangeWithTemporaryField({
				start: change.start,
				end: change.end,
				expectedText: change.expectedText
			});
			if (!nativeField) {
				throw new Error('Word did not return a temporary citation field');
			}
			assignments.push({
				field: nativeField,
				itemID: change.citationItems[0].id
			});
		}

		const registration = await registerNativeCitations(
			context.session, context.integration, assignments
		);
		await word.commitUndoTransaction(transaction);
		return {
			status: 'inserted_unsaved',
			applied: registration.registered,
			backupPath: backup.path
		};
	}
	catch (error) {
		if (transaction !== undefined) {
			try {
				if (await word.rollbackUndoTransaction(transaction) !== true) {
					throw new Error('Word rollback was not confirmed');
				}
			}
			catch (rollbackError) {
				throw new AggregateError(
					[error, rollbackError],
					'Word conversion and rollback failed; recover from verified backup'
				);
			}
		}
		// Zotero session state could now be stale even after Word undo.
		// The future native command must rebuild/reload it after a rollback.
		throw error;
	}
}

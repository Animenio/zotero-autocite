"use strict";

/**
 * Prepares native Zotero citation inputs without editing Word or serializing fields.
 * The Word adapter will locate ranges; Zotero.Integration.Session will create
 * citation objects, format citations and update the bibliography.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

import { buildCitationPlan } from './resolutionPlanner.mjs';
import { createZoteroNativeResolver } from './zoteroNativeLookup.mjs';

/**
 * Create an all-or-nothing plan for existing Zotero item references.
 *
 * @param {string} text - Snapshot of a single supported Word text story.
 * @param {Object} zotero - Zotero namespace (injected for unit tests).
 * @returns {Promise<Object>} Plan of document offsets and native citationItems
 */
export async function prepareNativeCitationBatch(text, zotero) {
	let plan = await buildCitationPlan(text, createZoteroNativeResolver(zotero));
	let problems = plan.occurrences.filter(x => x.status !== 'RESOLVED')
		.map(x => ({ marker: x.raw, start: x.start, status: x.status, reason: x.reason }));

	if (problems.length) {
		// Important: even successfully resolved markers are NOT applied.
		return { status: 'blocked', changes: [], problems, counts: plan.counts };
	}

	let changes = [];
	for (let marker of plan.replacements) {
		if (!Number.isSafeInteger(marker.item.itemID) || marker.item.itemID <= 0) {
			return {
				status: 'blocked',
				changes: [],
				problems: [{
					marker: marker.raw,
					start: marker.start,
					status: 'ERROR',
					reason: 'Source lacks a valid Zotero database item ID'
				}],
				counts: plan.counts
			};
		}

		changes.push({
			start: marker.start,
			end: marker.end,
			raw: marker.raw,
			library: marker.item.library,
			itemKey: marker.item.itemKey,
			// This is the Zotero-native citation input shape, NOT a serialized
			// Word field or an independently generated CSL citationID.
			citationItems: [{ id: marker.item.itemID }]
		});
	}

	return {
		status: changes.length ? 'ready' : 'empty',
		changes,
		problems: [],
		counts: plan.counts
	};
}

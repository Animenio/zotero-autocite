"use strict";

/**
 * Read-only adapter for Zotero's library and item APIs.
 *
 * This is an upstream candidate, not a Word insertion implementation.
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

const ZOTERO_ITEM_KEY_RE = /^[23456789ABCDEFGHIJKLMNPQRSTUVWXYZ]{8}$/;

/**
 * Construct a resolver for the existing read-only citation planner.
 * Only existing, explicitly scoped Zotero items are supported.
 *
 * @param {Object} zotero - Zotero runtime namespace; injectable for tests
 * @returns {Object} Resolver compatible with buildCitationPlan()
 */
export function createZoteroNativeResolver(zotero) {
	if (!zotero?.Libraries || !zotero?.Groups || !zotero?.Items) {
		throw new TypeError('Expected Zotero Libraries, Groups and Items APIs');
	}

	return {
		/**
		 * @param {{library: string, key: string}} reference
		 * @returns {Promise<Object>} Resolved bibliographic identity or error status
		 */
		async resolveZoteroItem(reference) {
			if (!reference || typeof reference.library !== 'string'
				|| typeof reference.key !== 'string'
				|| !ZOTERO_ITEM_KEY_RE.test(reference.key)) {
				return { status: 'error', message: 'Invalid Zotero reference' };
			}

			let libraryID;
			if (reference.library === 'user') {
				libraryID = zotero.Libraries.userLibraryID;
			}
			else {
				let groupMatch = /^group:([1-9][0-9]*)$/.exec(reference.library);
				if (!groupMatch) {
					return { status: 'error', message: 'Unsupported library scope' };
				}
				let groupID = Number(groupMatch[1]);
				if (!Number.isSafeInteger(groupID)) {
					return { status: 'error', message: 'Invalid group identifier' };
				}
				libraryID = zotero.Groups.getLibraryIDFromGroupID(groupID);
			}

			if (!Number.isSafeInteger(libraryID) || libraryID <= 0) {
				return { status: 'missing' };
			}

			try {
				let item = await zotero.Items.getByLibraryAndKeyAsync(libraryID, reference.key);
				if (!item) {
					return { status: 'missing' };
				}
				if (item.libraryID !== libraryID || item.key !== reference.key) {
					return { status: 'error', message: 'Item identity does not match scope' };
				}
				if (item.deleted || item.isFeedItem
					|| typeof item.isRegularItem !== 'function' || !item.isRegularItem()) {
					return { status: 'error', message: 'Item cannot be cited' };
				}

				return {
					status: 'found',
					item: {
						library: reference.library,
						itemKey: reference.key,
						title: item.getDisplayTitle(),
						doi: item.getField('DOI')
					}
				};
			}
			catch (e) {
				// Do not substitute an item from another library or import metadata.
				return { status: 'error', message: 'Zotero item lookup failed' };
			}
		},

		async resolveAlias() {
			return { status: 'error', message: 'Local AutoCite aliases are not portable' };
		},

		async resolveDOI() {
			return { status: 'error', message: 'DOI lookup is outside the initial upstream scope' };
		}
	};
}

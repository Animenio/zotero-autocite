// SPDX-License-Identifier: AGPL-3.0-or-later
#include "MarkerRangeValidator.h"

#include <stdexcept>
#include <vector>

using namespace autocite;

int main() {
	const auto check = [](bool condition) {
		if (!condition) throw std::runtime_error("MarkerRangeValidator test failed");
	};
	const std::u16string story = u"A \U0001F600 [[ZOTERO:user/HJVM9AMK]] B";
	const auto index = story.find(u"[[ZOTERO:");
	check(index != std::u16string::npos);
	const std::u16string expected = u"[[ZOTERO:user/HJVM9AMK]]";
	const MarkerRange marker{100 + static_cast<std::int64_t>(index),
		100 + static_cast<std::int64_t>(index) + static_cast<std::int64_t>(expected.size()),
		expected};
	check(ValidateMarkerRanges(story, 100, {marker}, {}) == ValidationStatus::Ready);
	check(ValidateMarkerRanges(story, 100, {}, {}) == ValidationStatus::Empty);
	check(ValidateMarkerRanges(story, -1, {marker}, {}) == ValidationStatus::InvalidStory);
	check(ValidateMarkerRanges(story, 100,
		{{marker.start, marker.end, u"[[ZOTERO:user/ABCDEFGH]]"}}, {}) == ValidationStatus::ChangedText);
	check(ValidateMarkerRanges(story, 100, {marker},
		{{marker.start + 1, marker.end - 1}}) == ValidationStatus::FieldCollision);
	check(ValidateMarkerRanges(story, 100, {marker},
		{{99, 100}}) == ValidationStatus::InvalidRange);
	check(ValidateMarkerRanges(story, 100,
		{{marker.start, marker.start, u""}}, {}) == ValidationStatus::InvalidRange);
	const std::u16string two = u"[[ZOTERO:user/HJVM9AMK]] and [[ZOTERO:user/HJVM9AMK]]";
	const std::int64_t secondStart = static_cast<std::int64_t>(expected.size()) + 5;
	const MarkerRange right{secondStart, secondStart + static_cast<std::int64_t>(expected.size()), expected};
	const MarkerRange left{0, static_cast<std::int64_t>(expected.size()), expected};
	check(ValidateMarkerRanges(two, 0, {right, left}, {}) == ValidationStatus::Ready);
	check(ValidateMarkerRanges(two, 0, {left, right}, {}) == ValidationStatus::NotDescending);
	return 0;
}

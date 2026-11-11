// SPDX-License-Identifier: AGPL-3.0-or-later
#include "MarkerRangeValidator.h"

#include <limits>

namespace autocite {

ValidationStatus ValidateMarkerRanges(
	std::u16string_view storyText,
	std::int64_t storyStart,
	const std::vector<MarkerRange>& markers,
	const std::vector<ProtectedRange>& fields) {
	if (storyStart < 0 || storyStart > std::numeric_limits<std::int32_t>::max()
		|| storyText.size() > static_cast<std::size_t>(
			std::numeric_limits<std::int32_t>::max() - storyStart)) {
		return ValidationStatus::InvalidStory;
	}
	const std::int64_t storyEnd = storyStart + static_cast<std::int64_t>(storyText.size());
	for (const auto& field : fields) {
		if (field.start < storyStart || field.end <= field.start || field.end > storyEnd) {
			return ValidationStatus::InvalidRange;
		}
	}
	if (markers.empty()) return ValidationStatus::Empty;

	std::int64_t previousStart = storyEnd + 1;
	for (const auto& marker : markers) {
		if (marker.start < storyStart || marker.end <= marker.start || marker.end > storyEnd) {
			return ValidationStatus::InvalidRange;
		}
		if (marker.end > previousStart) {
			return ValidationStatus::NotDescending;
		}
		const auto begin = static_cast<std::size_t>(marker.start - storyStart);
		const auto length = static_cast<std::size_t>(marker.end - marker.start);
		if (marker.expected.size() != length || storyText.substr(begin, length) != marker.expected) {
			return ValidationStatus::ChangedText;
		}
		for (const auto& field : fields) {
			if (marker.start < field.end && field.start < marker.end) {
				return ValidationStatus::FieldCollision;
			}
		}
		previousStart = marker.start;
	}
	return ValidationStatus::Ready;
}

} // namespace autocite

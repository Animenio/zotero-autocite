// SPDX-License-Identifier: AGPL-3.0-or-later
#pragma once

#include <cstdint>
#include <string>
#include <string_view>
#include <vector>

namespace autocite {

struct MarkerRange {
	std::int64_t start;
	std::int64_t end;
	std::u16string expected;
};

struct ProtectedRange {
	std::int64_t start;
	std::int64_t end;
};

enum class ValidationStatus {
	Ready,
	Empty,
	InvalidStory,
	InvalidRange,
	NotDescending,
	ChangedText,
	FieldCollision
};

// Word offsets and marker text are measured in UTF-16 code units.
// All ranges are half-open and absolute in the main story.
// No COM calls or edits are performed by this function.
ValidationStatus ValidateMarkerRanges(
	std::u16string_view storyText,
	std::int64_t storyStart,
	const std::vector<MarkerRange>& markers,
	const std::vector<ProtectedRange>& fields);

} // namespace autocite

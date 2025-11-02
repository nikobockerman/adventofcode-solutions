#pragma once

#include <charconv>
#include <ranges>
#include <stdexcept>
#include <type_traits>

template <typename TResult, typename TRange>
  requires(std::ranges::contiguous_range<TRange> &&
           std::ranges::sized_range<TRange> &&
           std::is_same_v<std::ranges::range_value_t<TRange>, char>)
constexpr auto convert(const TRange& range) -> TResult {
  if (std::ranges::empty(range)) {
    throw std::runtime_error("Empty string to convert");
  }

  TResult value{};
  const auto* begin = &*range.begin();
  const auto* pastEnd = &*range.end();
  auto [ptr, ec]{std::from_chars(begin, pastEnd, value)};
  if (ec == std::errc()) {
    return value;
  }
  auto inputValue = std::string{begin, pastEnd};
  if (ec == std::errc::invalid_argument) {
    throw std::runtime_error("Invalid argument: " + inputValue);
  }
  if (ec == std::errc::result_out_of_range) {
    throw std::runtime_error("Result out of range: " + inputValue);
  }
  throw std::runtime_error("Conversion failed due to unknown reason");
}

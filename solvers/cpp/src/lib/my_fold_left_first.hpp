#pragma once

#include <algorithm>

#if !defined(TEST_MY_FOLD_LEFT_FIRST) && __cpp_lib_ranges_fold >= 202207L

inline constexpr auto MyFoldLeftFirst = std::ranges::fold_left_first;

#else

#include <functional>
#include <iterator>
#include <optional>
#include <ranges>

namespace internal {

class MyFoldLeftFirstFunction {
 public:
  template <std::input_iterator I, std::sentinel_for<I> S, typename Fn>
  constexpr auto operator()(I first, const S& last, Fn fn) const {
    using RetVal = typename std::iterator_traits<decltype(first)>::value_type;

    if (first == last) {
      return std::optional<RetVal>();
    }

    auto init{*first};
    return std::make_optional(std::ranges::fold_left(++first, last, init, fn));
  }

  template <std::ranges::input_range Rng, typename Fn>
  // NOLINTNEXTLINE(cppcoreguidelines-missing-std-forward)
  constexpr auto operator()(Rng&& rng, Fn fn) const {
    auto cur = std::ranges::begin(rng);
    auto end = std::ranges::end(rng);
    return (*this)(cur, end, fn);
  }
};

}  // namespace internal

inline constexpr internal::MyFoldLeftFirstFunction MyFoldLeftFirst{};

#endif

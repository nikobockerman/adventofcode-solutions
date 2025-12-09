#pragma once

#include <ranges>

#if defined(TEST_MY_ENUMERATE_VIEW) && __cpp_lib_ranges_enumerate >= 202302L

inline constexpr auto MyEnumerate = std::views::enumerate;

#else

namespace internal {

// Only supported via MyEnumerate adaptor

template <std::ranges::viewable_range Rng>
class MyEnumerateView
  : public std::ranges::view_interface<MyEnumerateView<Rng>> {
  using Base = Rng;

  class Iterator {
    using BaseIter = std::ranges::iterator_t<Base>;
    using BaseSentinel = std::ranges::sentinel_t<Base>;

   public:
    using difference_type = std::ranges::range_difference_t<Base>;
    using value_type =
      std::tuple<difference_type, std::ranges::range_value_t<Base>>;

    explicit Iterator(BaseIter begin, BaseSentinel end) noexcept
      : _cur{std::move(begin)}, _end{std::move(end)} {}

    constexpr auto operator*() const noexcept(noexcept(
      std::tuple<difference_type, std::ranges::range_reference_t<Base>>(
        _count, *_cur))) {
      return std::tuple<difference_type, std::ranges::range_reference_t<Base>>(
        _count, *_cur);
    }

    constexpr Iterator& operator++() noexcept(
      noexcept(std::ranges::advance(_cur, 1)) && noexcept(++_count)) {
      std::ranges::advance(_cur, 1);
      ++_count;
      return *this;
    }
    constexpr void operator++(int) noexcept(noexcept(++(*this))) { ++(*this); }

    constexpr bool operator==(const Iterator& o) const
      noexcept(noexcept(_cur == o._cur)) {
      return _cur == o._cur;
    }
    constexpr bool operator==(std::default_sentinel_t /*unused*/) const
      noexcept(noexcept(_cur == _end)) {
      return _cur == _end;
    }

   private:
    BaseIter _cur;
    BaseSentinel _end;
    difference_type _count{0};
  };

 public:
  explicit MyEnumerateView(Rng&& rng) noexcept(
    noexcept(Base(std::views::all(std::move(rng)))))
    : _base{std::views::all(std::move(rng))} {}

  [[nodiscard]] constexpr auto begin() const
    noexcept(noexcept(Iterator(std::ranges::begin(_base),
                               std::ranges::end(_base))))
    requires std::ranges::range<const Base>
  {
    return Iterator{std::ranges::begin(_base), std::ranges::end(_base)};
  }
  [[nodiscard]] constexpr auto begin() noexcept(
    noexcept(Iterator(std::ranges::begin(_base), std::ranges::end(_base)))) {
    return Iterator{std::ranges::begin(_base), std::ranges::end(_base)};
  }

  static constexpr auto end() noexcept { return std::default_sentinel; }

 private:
  Base _base;
};

class MyEnumerateAdaptorClosure
  : public std::ranges::range_adaptor_closure<MyEnumerateAdaptorClosure> {
 public:
  template <std::ranges::viewable_range Rng>
  constexpr auto operator()(Rng&& rng) const noexcept(
    noexcept(MyEnumerateView<decltype(std::views::all(std::forward<Rng>(rng)))>(
      std::views::all(std::forward<Rng>(rng))))) {
    auto rngAll = std::views::all(std::forward<Rng>(rng));
    return MyEnumerateView<decltype(rngAll)>{std::move(rngAll)};
  }
};

}  // namespace internal

inline constexpr internal::MyEnumerateAdaptorClosure MyEnumerate{};

#endif

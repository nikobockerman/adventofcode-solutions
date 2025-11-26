#pragma once

#include <ranges>

#if !defined(TEST_MY_SLIDE_VIEW) && __cpp_lib_ranges_slide >= 202202L

inline constexpr auto MySlide = std::views::slide;

#else

#include <cstddef>

namespace internal {

// Only supported via MySlide adaptor

template <std::ranges::viewable_range Rng>
class MySlideView : public std::ranges::view_interface<MySlideView<Rng>> {
  using Base = std::views::all_t<Rng>;

  class Iterator {
    using BaseIter = std::ranges::iterator_t<Base>;

   public:
    using difference_type = std::ptrdiff_t;
    using value_type = decltype(std::ranges::subrange<BaseIter>());

    explicit Iterator(BaseIter begin, BaseIter end, std::size_t n) noexcept(
      noexcept(std::ranges::advance(begin, n, end)))
      : _curSlideBegin{std::move(begin)},
        _curSlideEnd{_curSlideBegin},
        _end{std::move(end)} {
      auto reachedN = std::ranges::advance(_curSlideEnd, n, _end) == 0;
      if (!reachedN) {
        _pastEnd = true;
      }
    }

    constexpr auto operator*() const
      noexcept(noexcept(std::ranges::subrange(_curSlideBegin, _curSlideEnd))) {
      return std::ranges::subrange(_curSlideBegin, _curSlideEnd);
    }

    constexpr Iterator& operator++() noexcept(
      noexcept(std::ranges::advance(_curSlideBegin, 1)) &&
      noexcept(std::ranges::advance(_curSlideEnd, 1))) {
      std::ranges::advance(_curSlideBegin, 1);
      if (_curSlideEnd != _end) {
        std::ranges::advance(_curSlideEnd, 1);
      } else {
        _pastEnd = true;
      }
      return *this;
    }
    constexpr void operator++(int) noexcept(noexcept(++(*this))) { ++(*this); }

    constexpr bool operator==(const Iterator& o) const
      noexcept(noexcept(_curSlideBegin == o._curSlideBegin)) {
      return _curSlideBegin == o._curSlideBegin;
    }
    constexpr bool operator==(
      std::default_sentinel_t /*unused*/) const noexcept {
      return _pastEnd;
    }

   private:
    BaseIter _curSlideBegin;
    BaseIter _curSlideEnd;
    BaseIter _end;
    bool _pastEnd{false};
  };

 public:
  explicit MySlideView(Rng&& rng, std::size_t n) noexcept(
    noexcept(Base(std::views::all(std::move(rng)))))
    : _base{std::views::all(std::move(rng))}, _n{n} {}

  [[nodiscard]] constexpr auto begin() const
    noexcept(noexcept(Iterator(std::ranges::begin(_base),
                               std::ranges::end(_base), _n)))
    requires std::ranges::range<const Base>
  {
    return Iterator{std::ranges::begin(_base), std::ranges::end(_base), _n};
  }
  [[nodiscard]] constexpr auto begin() noexcept(noexcept(
    Iterator(std::ranges::begin(_base), std::ranges::end(_base), _n))) {
    return Iterator{std::ranges::begin(_base), std::ranges::end(_base), _n};
  }

  static constexpr auto end() noexcept { return std::default_sentinel; }

 private:
  Base _base;
  std::size_t _n;
};

class MySlideAdaptorClosure
  : public std::ranges::range_adaptor_closure<MySlideAdaptorClosure> {
 public:
  constexpr explicit MySlideAdaptorClosure(std::size_t n) noexcept : _n{n} {}

  template <std::ranges::viewable_range Rng>
  constexpr auto operator()(Rng&& rng) const noexcept(
    noexcept(MySlideView<decltype(std::views::all(std::forward<Rng>(rng)))>(
      std::views::all(std::forward<Rng>(rng)), _n))) {
    auto rngAll = std::views::all(std::forward<Rng>(rng));
    return MySlideView<decltype(rngAll)>{std::move(rngAll), _n};
  }

 private:
  std::size_t _n;
};

}  // namespace internal

class MySlideAdaptor {
 public:
  constexpr internal::MySlideAdaptorClosure operator()(
    std::size_t n) const noexcept {
    return internal::MySlideAdaptorClosure{n};
  }
};

inline constexpr MySlideAdaptor MySlide{};

#endif

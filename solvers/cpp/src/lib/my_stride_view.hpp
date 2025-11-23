#pragma once

#include <ranges>

#ifdef TEST_MY_STRIDE_VIEW
#define USE_MY_STRIDE_VIEW
#else
#ifndef __cpp_lib_ranges_stride
#define USE_MY_STRIDE_VIEW
#endif
#endif

#ifndef USE_MY_STRIDE_VIEW

template <typename T>
constexpr auto MyStride(T&& n) {
  return std::views::stride(std::forward<T>(n));
}

#else

#include <cstddef>

namespace internal {

// Only supported via MyStride adaptor

template <std::ranges::viewable_range Rng>
class MyStrideView : public std::ranges::view_interface<MyStrideView<Rng>> {
  using Base = std::views::all_t<Rng>;

  class Iterator {
    using BaseIter = std::ranges::iterator_t<Base>;

   public:
    using difference_type = std::ptrdiff_t;
    using value_type = std::iter_value_t<BaseIter>;

    explicit Iterator(BaseIter begin, BaseIter end, std::size_t n) noexcept
      : _cur{std::move(begin)}, _end{std::move(end)}, _n{n} {
      if (_n == 0) {
        _cur = _end;
      }
    }

    constexpr auto operator*() const noexcept(noexcept(*_cur)) { return *_cur; }

    constexpr Iterator& operator++() noexcept {
      std::ranges::advance(_cur, _n, _end);
      return *this;
    }
    constexpr void operator++(int) noexcept { ++*this; }

    constexpr bool operator==(const Iterator& o) const noexcept {
      return _cur == o._cur;
    }
    constexpr bool operator==(
      std::default_sentinel_t /*unused*/) const noexcept {
      return _cur == _end;
    }

   private:
    BaseIter _cur;
    BaseIter _end;
    std::size_t _n;
  };

 public:
  explicit MyStrideView(Rng&& rng, std::size_t n) noexcept
    : _base{std::views::all(std::move(rng))}, _n{n} {}

  [[nodiscard]] constexpr auto begin() const noexcept
    requires std::ranges::range<const Base>
  {
    return Iterator{std::ranges::begin(_base), std::ranges::end(_base), _n};
  }
  [[nodiscard]] constexpr auto begin() noexcept {
    return Iterator{std::ranges::begin(_base), std::ranges::end(_base), _n};
  }

  static constexpr auto end() noexcept { return std::default_sentinel; }

 private:
  Base _base;
  std::size_t _n;
};

class MyStrideAdaptorClosure
  : public std::ranges::range_adaptor_closure<MyStrideAdaptorClosure> {
 public:
  constexpr explicit MyStrideAdaptorClosure(std::size_t n) noexcept : _n{n} {}

  template <std::ranges::viewable_range Rng>
  constexpr auto operator()(Rng&& rng) const noexcept {
    auto rngAll = std::views::all(std::forward<Rng>(rng));
    return MyStrideView<decltype(rngAll)>(std::move(rngAll), _n);
  }

 private:
  std::size_t _n;
};

}  // namespace internal

class MyStrideAdaptor {
 public:
  constexpr internal::MyStrideAdaptorClosure operator()(
    std::size_t n) const noexcept {
    return internal::MyStrideAdaptorClosure{n};
  }
};

inline constexpr MyStrideAdaptor MyStride{};

#endif

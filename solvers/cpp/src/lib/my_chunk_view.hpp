#pragma once

#include <ranges>

#if !defined(TEST_MY_CHUNK_VIEW) && __cpp_lib_ranges_chunk >= 202202L

inline constexpr auto MyChunk = std::views::chunk;

#else

namespace internal {

// Only supported via MyChunk adaptor

template <std::ranges::viewable_range Rng>
class MyChunkView : public std::ranges::view_interface<MyChunkView<Rng>> {
  using Base = Rng;

  class Iterator {
    using BaseIter = std::ranges::iterator_t<Base>;
    using BaseSentinel = std::ranges::sentinel_t<Base>;

   public:
    using difference_type = std::ranges::range_difference_t<Base>;
    using value_type = decltype(std::ranges::subrange<BaseIter>());

    explicit Iterator(BaseIter begin, BaseSentinel end, std::size_t n) noexcept(
      noexcept(std::ranges::advance(_curChunkEnd, _n, _end)))
      : _curChunkBegin{std::move(begin)},
        _curChunkEnd{_curChunkBegin},
        _end{std::move(end)},
        _n{n} {
      std::ranges::advance(_curChunkEnd, _n, _end);
    }

    constexpr auto operator*() const
      noexcept(noexcept(std::ranges::subrange(_curChunkBegin, _curChunkEnd))) {
      return std::ranges::subrange(_curChunkBegin, _curChunkEnd);
    }

    constexpr Iterator& operator++() noexcept(
      noexcept(std::ranges::advance(_curChunkBegin, _n, _end)) &&
      noexcept(std::ranges::advance(_curChunkEnd, _n, _end))) {
      std::ranges::advance(_curChunkBegin, _n, _end);
      std::ranges::advance(_curChunkEnd, _n, _end);
      return *this;
    }
    constexpr void operator++(int) noexcept(noexcept(++(*this))) { ++(*this); }

    constexpr bool operator==(const Iterator& o) const
      noexcept(noexcept(_curChunkBegin == o._curChunkBegin)) {
      return _curChunkBegin == o._curChunkBegin;
    }
    constexpr bool operator==(std::default_sentinel_t /*unused*/) const
      noexcept(noexcept(_curChunkBegin == _end)) {
      return _curChunkBegin == _end;
    }

   private:
    BaseIter _curChunkBegin;
    BaseIter _curChunkEnd;
    BaseSentinel _end;
    std::size_t _n;
  };

 public:
  explicit MyChunkView(Rng&& rng, std::size_t n) noexcept(
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

class MyChunkAdaptorClosure
  : public std::ranges::range_adaptor_closure<MyChunkAdaptorClosure> {
 public:
  constexpr explicit MyChunkAdaptorClosure(std::size_t n) noexcept : _n{n} {}

  template <std::ranges::viewable_range Rng>
  constexpr auto operator()(Rng&& rng) const noexcept(
    noexcept(MyChunkView<decltype(std::views::all(std::forward<Rng>(rng)))>(
      std::views::all(std::forward<Rng>(rng)), _n))) {
    auto rngAll = std::views::all(std::forward<Rng>(rng));
    return MyChunkView<decltype(rngAll)>{std::move(rngAll), _n};
  }

 private:
  std::size_t _n;
};

}  // namespace internal

class MyChunkAdaptor {
 public:
  constexpr internal::MyChunkAdaptorClosure operator()(
    std::size_t n) const noexcept {
    return internal::MyChunkAdaptorClosure{n};
  }
};

inline constexpr MyChunkAdaptor MyChunk{};

#endif

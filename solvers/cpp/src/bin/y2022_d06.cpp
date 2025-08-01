#include "answer.hpp"
#include "solver.hpp"

#include <algorithm>
#include <cstddef>
#include <iterator>
#include <ranges>
#include <string_view>
#include <vector>

namespace ranges = std::ranges;
namespace views = std::views;
using namespace std::string_literals;
using namespace std::string_view_literals;

namespace {

template <std::size_t windowSize>
constexpr auto firstDistinctWindow(auto &&range) {
  auto notStarts =
    range | views::slide(windowSize) | views::take_while([](auto &&window) {
      auto vector = window | ranges::to<std::vector>();
      ranges::sort(vector);
      return ranges::adjacent_find(vector) != vector.end();
    });
  return ranges::distance(notStarts) + windowSize;
}

}  // namespace

auto solver::p1(std::string_view inputStr) -> Answer {
  return firstDistinctWindow<4>(inputStr);
}

auto solver::p2(std::string_view inputStr) -> Answer {
  constexpr auto windowSize = 14;
  return firstDistinctWindow<windowSize>(inputStr);
}

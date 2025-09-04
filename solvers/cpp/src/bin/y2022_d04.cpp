#include "answer.hpp"
#include "convert.hpp"
#include "solver.hpp"
#include "utils.hpp"

#include <algorithm>
#include <ranges>
#include <string_view>
#include <vector>

namespace ranges = std::ranges;
namespace views = std::views;
using namespace std::string_view_literals;

namespace {

class Section {
 public:
  unsigned start;
  unsigned end;
};

constexpr auto getSection(auto&& range) -> Section {
  auto values = range | views::split('-') | ranges::to<std::vector>();
  return {convert<unsigned>(values.at(0)), convert<unsigned>(values.at(1))};
}

constexpr auto getSectionPair(auto&& line) {
  auto pairs = line | views::split(',') | ranges::to<std::vector>();
  return std::make_pair(getSection(pairs.at(0)), getSection(pairs.at(1)));
}

constexpr auto getSectionPairs(auto&& range) {
  return splitLinesUntilEmpty(range) |
         views::transform([](auto&& line) { return getSectionPair(line); });
}

constexpr auto isContained(auto& containerSection, auto& checkedSection) {
  return containerSection.start <= checkedSection.start &&
         containerSection.end >= checkedSection.end;
}

constexpr auto areContained(auto& sectionPair) {
  return isContained(sectionPair.first, sectionPair.second) ||
         isContained(sectionPair.second, sectionPair.first);
}

constexpr auto solve1(auto inputStr) {
  auto pairs = getSectionPairs(inputStr);
  return ranges::count_if(pairs,
                          [](const auto& pair) { return areContained(pair); });
}

}  // namespace

auto solver::p1(std::string_view inputStr) -> Answer {
  return solve1(inputStr);
}

namespace {

constexpr auto areSeparate(auto& sectionPair) {
  return sectionPair.first.end < sectionPair.second.start ||
         sectionPair.second.end < sectionPair.first.start;
}

constexpr auto overlap(auto& sectionPair) { return !areSeparate(sectionPair); }

constexpr auto solve2(auto inputStr) {
  auto pairs = getSectionPairs(inputStr);
  return ranges::count_if(pairs,
                          [](const auto& pair) { return overlap(pair); });
}

}  // namespace

auto solver::p2(std::string_view inputStr) -> Answer {
  return solve2(inputStr);
}

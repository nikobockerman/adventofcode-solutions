#include "answer.hpp"
#include "convert.hpp"
#include "my_enumerate_view.hpp"
#include "my_fold_left_first.hpp"
#include "solver.hpp"
#include "utils.hpp"

#include <spdlog/spdlog.h>

#include <algorithm>
#include <array>
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <format>
#include <functional>
#include <limits>
#include <optional>
#include <queue>
#include <ranges>
#include <stdexcept>
#include <string_view>
#include <utility>
#include <vector>

namespace ranges = std::ranges;
namespace views = std::views;
using namespace std::string_view_literals;

namespace {

enum class Operator : std::uint8_t { Plus, Multiply, Concatenate };

template <bool allowConcatenateOperator,
          size_t size = allowConcatenateOperator ? 3 : 2>
consteval auto getOperators() -> std::array<const Operator, size> {
  if constexpr (allowConcatenateOperator) {
    return std::array<const Operator, size>{Operator::Multiply, Operator::Plus,
                                            Operator::Concatenate};
  }
  return std::array<const Operator, size>{Operator::Multiply, Operator::Plus};
}

struct EquationState {
  uint64_t eqResult;
  uint64_t nextValue;
  size_t nextIndex;
};

auto operator<(const EquationState& lhs, const EquationState& rhs) -> bool {
  return lhs.eqResult < rhs.eqResult;
}

template <bool allowConcatenationOperator>
auto applyOperator(const uint64_t eqResult, const uint64_t nextValue,
                   const Operator operator_) -> uint64_t {
  switch (operator_) {
    case Operator::Plus:
      return eqResult + nextValue;
    case Operator::Multiply:
      return eqResult * nextValue;
    case Operator::Concatenate: {
      assert(allowConcatenationOperator);
      return convert<uint64_t>(std::format("{}{}", eqResult, nextValue));
    }
  }
  assert(false);
  return std::numeric_limits<uint64_t>::max();
}

[[nodiscard]] auto getNextValueAndIndex(const size_t index,
                                        const std::vector<uint64_t>& numbers)
  -> std::optional<std::pair<uint64_t, size_t>> {
  if (index >= numbers.size()) {
    return std::nullopt;
  }
  return std::make_pair(numbers[index], index + 1);
}

template <bool allowConcatenationOperator>
[[nodiscard]] auto equationCanBeTrue(const uint64_t expectedResult,
                                     const std::vector<uint64_t>& numbers)
  -> bool {
  std::priority_queue<EquationState> pq;
  pq.emplace(numbers[0], numbers[1], 2);

  constexpr auto operators = getOperators<allowConcatenationOperator>();
  while (!pq.empty()) {
    const auto [eqResult, nextValue, nextIndex] = pq.top();
    pq.pop();

    for (auto operator_ : operators) {
      auto newEqResult = applyOperator<allowConcatenationOperator>(
        eqResult, nextValue, operator_);
      if (newEqResult > expectedResult) {
        continue;
      }

      if (auto newNextInfo = getNextValueAndIndex(nextIndex, numbers)) {
        auto [newNextValue, newNextIndex] = *newNextInfo;
        pq.emplace(newEqResult, newNextValue, newNextIndex);
      } else if (newEqResult == expectedResult) {
        return true;
      }
    }
  }
  return false;
}

template <bool allowConcatenationOperator>
class PossibleEquation {
 public:
  PossibleEquation(uint64_t testResult, std::vector<uint64_t> numbers)
    : _testResult{testResult}, _numbers{std::move(numbers)} {
    if (_numbers.size() < 2) {
      throw std::runtime_error("Wrong number of numbers in equation");
    }
  }

  [[nodiscard]] auto canBeMadeTrue() const -> bool {
    return equationCanBeTrue<allowConcatenationOperator>(_testResult, _numbers);
  }

  [[nodiscard]] auto testResult() const -> uint64_t { return _testResult; }

 private:
  uint64_t _testResult;
  std::vector<uint64_t> _numbers;
};

template <bool allowConcatenationOperator>
auto solve(std::string_view input) {
  auto result = MyFoldLeftFirst(
    splitLinesUntilEmpty(input) | MyEnumerate |
      views::transform([](auto&& args) -> std::optional<uint64_t> {
        auto [index, line] = args;
        auto parts = line | views::split(':') | ranges::to<std::vector>();
        auto testValue = convert<uint64_t>(parts.at(0));
        auto values = parts.at(1) | views::drop(1) | views::split(' ') |
                      views::transform(
                        [](auto&& value) { return convert<uint64_t>(value); }) |
                      ranges::to<std::vector>();
        auto eq = PossibleEquation<allowConcatenationOperator>{
          testValue, std::move(values)};
        if (eq.canBeMadeTrue()) {
          spdlog::info("Possible Equation: {} -> {}", index, testValue);
          return eq.testResult();
        }
        return std::nullopt;
      }) |
      views::filter([](const auto& eqResult) { return eqResult.has_value(); }) |
      views::transform([](auto&& eqResult) {
        assert(eqResult.has_value());
        return eqResult.value();
      }),
    std::plus());
  if (!result) {
    throw std::runtime_error("No result");
  }
  return std::uint64_t{result.value()};
}

}  // namespace

auto solver::p1(const std::string_view inputStr) -> Answer {
  return solve<false>(inputStr);
}

auto solver::p2(const std::string_view inputStr) -> Answer {
  return solve<true>(inputStr);
}

#include "my_fold_left_first.hpp"
#include "solver.hpp"
#include "utils.hpp"

#include <spdlog/spdlog.h>

#include <convert.hpp>

namespace ranges = std::ranges;
namespace views = std::views;

namespace {

constexpr unsigned initialPosition = 50;
constexpr unsigned maxSteps = 100;

enum class Direction : std::uint8_t { Left, Right };

auto toLog(Direction dir) -> char {
  switch (dir) {
    case Direction::Left:
      return 'L';
    case Direction::Right:
      return 'R';
  }
  return '?';
}

class Rotation final {
 public:
  Direction _dir;
  unsigned _steps;
};

auto parseDirection(const char c) -> Direction {
  switch (c) {
    case 'L':
      return Direction::Left;
    case 'R':
      return Direction::Right;
    default:
      throw std::invalid_argument("Invalid direction: " + std::string{1, c});
  }
}

auto parseRotation(auto&& str) -> Rotation {
  auto stepsBegin = str.begin();
  ranges::advance(stepsBegin, 1, str.end());
  return Rotation{
    ._dir = parseDirection(*str.begin()),
    ._steps = convert<unsigned>(ranges::subrange(stepsBegin, str.end()))};
}

class Lock final {
 public:
  auto rotate(Rotation rotation) -> unsigned {
    auto zeros = rotation._steps / maxSteps;
    auto steps = rotation._steps % maxSteps;
    if (rotation._dir == Direction::Left) {
      if (steps > _position) {
        if (_position > 0) {
          ++zeros;
        }
        _position += maxSteps;
      }
      _position -= steps;
    } else {
      if (_position + steps > maxSteps) {
        ++zeros;
      }
      _position += steps;
      _position %= maxSteps;
    }
    spdlog::debug("Lock rotated: {}{} -> {} ({} zeros)", toLog(rotation._dir),
                  rotation._steps, _position, zeros);
    return zeros;
  }

  [[nodiscard]] constexpr auto position() const -> unsigned {
    return _position;
  }

 private:
  unsigned _position{initialPosition};
};

auto parseRotations(const std::string_view inputStr) {
  return splitLinesUntilEmpty(inputStr) |
         views::transform([](auto&& line) { return parseRotation(line); });
}

auto solve(const std::string_view inputStr, bool includeZerosDuringRotations)
  -> uint64_t {
  auto rotations = parseRotations(inputStr);
  auto result = MyFoldLeftFirst(
    rotations | views::transform([lock = Lock(), includeZerosDuringRotations](
                                   auto&& rotation) mutable -> unsigned {
      auto zerosDuringRotation = lock.rotate(rotation);
      auto zeros = lock.position() == 0 ? 1U : 0U;
      if (includeZerosDuringRotations) {
        zeros += zerosDuringRotation;
      }
      return zeros;
    }),
    std::plus{});
  if (!result) {
    throw std::runtime_error("No rotations");
  }
  return result.value();
}

}  // namespace

auto solver::p1(const std::string_view inputStr) -> Answer {
  return solve(inputStr, false);
}

auto solver::p2(std::string_view inputStr) -> Answer {
  return solve(inputStr, true);
}

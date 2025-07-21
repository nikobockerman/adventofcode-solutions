#include "solver.hpp"
#include "test_utils.hpp"

#include <gtest/gtest.h>

#include <string>
#include <string_view>

using namespace std::string_literals;
using namespace std::string_view_literals;

using T2022Day5 = TestFixture;

constexpr auto exampleInput = processExampleInput(R"input(
    [D]
[N] [C]
[Z] [M] [P]
 1   2   3

move 1 from 2 to 1
move 3 from 1 to 3
move 2 from 2 to 1
move 1 from 1 to 2
)input"sv);

TEST_F(T2022Day5, p1) {
  const auto exampleResult = "CMZ"s;  // NOLINT(misc-include-cleaner)
  verifyResult<std::string>(solver::p1(exampleInput), exampleResult);
}

TEST_F(T2022Day5, p2) {
  const auto exampleResult = "MCD"s;
  verifyResult<std::string>(solver::p2(exampleInput), exampleResult);
}

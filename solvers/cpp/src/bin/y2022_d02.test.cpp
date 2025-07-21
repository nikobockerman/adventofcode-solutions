#include "solver.hpp"
#include "test_utils.hpp"

#include <gtest/gtest.h>

#include <cstdint>
#include <string_view>

using namespace std::string_view_literals;

using T2022Day2 = TestFixture;

constexpr auto exampleInput = processExampleInput(R"input(
A Y
B X
C Z
)input"sv);

TEST_F(T2022Day2, p1) {
  constexpr auto exampleResult = 15;
  verifyResult<uint64_t>(solver::p1(exampleInput), exampleResult);
}

TEST_F(T2022Day2, p2) {
  constexpr auto exampleResult = 12;
  verifyResult<uint64_t>(solver::p2(exampleInput), exampleResult);
}

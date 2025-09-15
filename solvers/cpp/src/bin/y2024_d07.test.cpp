#include "solver.hpp"
#include "test_utils.hpp"

#include <gtest/gtest.h>

#include <cstdint>
#include <string_view>

using namespace std::string_view_literals;

using T2024Day7 = TestFixture;

constexpr auto exampleInput = processExampleInput(R"input(
190: 10 19
3267: 81 40 27
83: 17 5
156: 15 6
7290: 6 8 6 15
161011: 16 10 13
192: 17 8 14
21037: 9 7 18 13
292: 11 6 16 20
)input"sv);

TEST_F(T2024Day7, p1) {
  constexpr auto exampleResult = 3'749;
  verifyResult<uint64_t>(solver::p1(exampleInput), exampleResult);
}

TEST_F(T2024Day7, p2) {
  constexpr auto exampleResult = 11'387;
  verifyResult<uint64_t>(solver::p2(exampleInput), exampleResult);
}

#include "solver.hpp"
#include "test_utils.hpp"

#include <gtest/gtest.h>

#include <cstdint>
#include <string_view>

using namespace std::string_view_literals;

using T2022Day4 = TestFixture;

constexpr auto exampleInput = processExampleInput(R"input(
2-4,6-8
2-3,4-5
5-7,7-9
2-8,3-7
6-6,4-6
2-6,4-8
)input"sv);

TEST_F(T2022Day4, p1) {
  constexpr auto exampleResult = 2;
  verifyResult<int64_t>(solver::p1(exampleInput), exampleResult);
}

TEST_F(T2022Day4, p2) {
  constexpr auto exampleResult = 4;
  verifyResult<int64_t>(solver::p2(exampleInput), exampleResult);
}

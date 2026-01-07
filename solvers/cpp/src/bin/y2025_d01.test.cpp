#include "solver.hpp"
#include "test_utils.hpp"

#include <gtest/gtest.h>

#include <cstdint>
#include <string_view>

using namespace std::string_view_literals;

using T2025Day1 = TestFixture;

constexpr auto exampleInput = processExampleInput(R"input(
L68
L30
R48
L5
R60
L55
L1
L99
R14
L82
)input"sv);

TEST_F(T2025Day1, p1) {
  constexpr auto exampleResult = 3;
  verifyResult<uint64_t>(solver::p1(exampleInput), exampleResult);
}

TEST_F(T2025Day1, p2) {
  constexpr auto exampleResult = 6;
  verifyResult<uint64_t>(solver::p2(exampleInput), exampleResult);
}

#include "solver.hpp"
#include "test_utils.hpp"

#include <gtest/gtest.h>

#include <string_view>

using namespace std::string_view_literals;

using T2025Day2 = TestFixture;

constexpr auto exampleInput = processExampleInput(R"input(
11-22,95-115,998-1012,1188511880-1188511890,222220-222224,1698522-1698528,446443-446449,38593856-38593862,565653-565659,824824821-824824827,2121212118-2121212124
)input"sv);

TEST_F(T2025Day2, p1) {
  constexpr auto exampleResult = 1'227'775'554;
  verifyResult<uint64_t>(solver::p1(exampleInput), exampleResult);
}

TEST_F(T2025Day2, p2) {
  constexpr auto exampleResult = 4'174'379'265;
  verifyResult<uint64_t>(solver::p2(exampleInput), exampleResult);
}

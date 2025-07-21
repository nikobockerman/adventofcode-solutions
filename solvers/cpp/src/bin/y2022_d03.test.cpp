#include "solver.hpp"
#include "test_utils.hpp"

#include <gtest/gtest.h>

#include <cstdint>
#include <string_view>

using namespace std::string_view_literals;

using T2022Day3 = TestFixture;

constexpr auto exampleInput = processExampleInput(R"input(
vJrwpWtwJgWrhcsFMMfFFhFp
jqHRNqRjqzjGDLGLrsFMfFZSrLrFZsSL
PmmdzqPrVvPwwTWBwg
wMqvLMZHhHMvwLHjbvcjnnSBnvTQFn
ttgJtRGJQctTZtZT
CrZsJsPPZsGzwwsLwLmpwMDw
)input"sv);

TEST_F(T2022Day3, p1) {
  constexpr auto exampleResult = 157;
  verifyResult<uint64_t>(solver::p1(exampleInput), exampleResult);
}

TEST_F(T2022Day3, p2) {
  constexpr auto exampleResult = 70;
  verifyResult<uint64_t>(solver::p2(exampleInput), exampleResult);
}

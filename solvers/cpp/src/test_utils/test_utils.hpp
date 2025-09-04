#pragma once

#include "answer.hpp"

#include <gtest/gtest.h>

void enableDebugLogging();

class TestFixture : public ::testing::Test {
 protected:
  void SetUp() override { enableDebugLogging(); }
};

template <typename TAnswer>
auto verifyResult(const Answer& result, const TAnswer& expected) {
  ASSERT_TRUE(std::holds_alternative<TAnswer>(result));
  EXPECT_EQ(std::get<TAnswer>(result), expected);
}

constexpr auto processExampleInput(auto input) {
  input.remove_prefix(1);
  return input;
}

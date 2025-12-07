#define TEST_MY_FOLD_LEFT_FIRST
#include "my_fold_left_first.hpp"

#if defined(_LIBCPP_VERSION) && __cpp_lib_ranges_fold >= 202207L
#error "libc++ started supporting std::ranges::fold_left_first. Use it directly"
#endif

#include "test_utils.hpp"

#include <gtest/gtest.h>

#include <vector>

namespace views = std::views;

TEST(MyFoldLeftFirst, Empty) {
  constexpr std::vector<int> data{};
  auto result = MyFoldLeftFirst(data | views::all, std::plus{});
  EXPECT_FALSE(result.has_value());
  result = MyFoldLeftFirst(data.begin(), data.end(), std::plus{});
  EXPECT_FALSE(result.has_value());
}

TEST(MyFoldLeftFirst, One) {
  const std::vector<int> data{2};
  auto result = MyFoldLeftFirst(data | views::all, std::plus{});
  ASSERT_HAS_VALUE(result);
  EXPECT_EQ(*result, 2);

  result = MyFoldLeftFirst(data.begin(), data.end(), std::plus{});
  ASSERT_HAS_VALUE(result);
  EXPECT_EQ(*result, 2);
}

TEST(MyFoldLeftFirst, Two) {
  const std::vector<int> data{2, 3};
  auto result = MyFoldLeftFirst(data | views::all, std::plus{});
  ASSERT_HAS_VALUE(result);
  EXPECT_EQ(*result, 5);

  result = MyFoldLeftFirst(data.begin(), data.end(), std::plus{});
  ASSERT_HAS_VALUE(result);
  EXPECT_EQ(*result, 5);
}

TEST(MyFoldLeftFirst, Multiple) {
  constexpr int End = 10;
  constexpr int ExpectedResult = 1 + 2 + 3 + 4 + 5 + 6 + 7 + 8 + 9;
  auto result = MyFoldLeftFirst(views::iota(1, End), std::plus{});
  ASSERT_HAS_VALUE(result);
  EXPECT_EQ(*result, ExpectedResult);

  auto iota = views::iota(1, End);
  result = MyFoldLeftFirst(iota.begin(), iota.end(), std::plus{});
  ASSERT_HAS_VALUE(result);
  EXPECT_EQ(*result, ExpectedResult);
}

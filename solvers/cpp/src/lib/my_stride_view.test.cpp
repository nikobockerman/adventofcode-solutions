#define TEST_MY_STRIDE_VIEW
#include "my_stride_view.hpp"

#include <gtest/gtest.h>

#include <ranges>
#include <string>
#include <string_view>

#ifdef __cpp_lib_ranges_stride
#ifdef _LIBCPP_VERSION
#error "libc++ started supporting std::views::stride. Use it directly"
#endif
#endif

namespace ranges = std::ranges;
namespace views = std::views;

TEST(MyStrideView, BetweenPipes) {
  const std::string data{"123456789"};
  auto processed = data | views::drop(1) | MyStride(3) | views::take(3) |
                   ranges::to<std::string>();
  EXPECT_EQ(processed, "258");
}

TEST(MyStrideView, Empty) {
  constexpr std::vector<int> empty;
  auto processed = empty | MyStride(2) | ranges::to<std::vector>();
  EXPECT_TRUE(processed.empty());
}

TEST(MyStrideView, One) {
  constexpr std::array<int, 1> one{1};
  auto processed = one | MyStride(2) | ranges::to<std::vector>();
  ASSERT_EQ(processed.size(), 1);
  EXPECT_EQ(processed[0], 1);
}

TEST(MyStrideView, ZeroStride) {
  constexpr std::array<int, 5> data{1, 2, 3, 4, 5};
  auto processed = data | MyStride(0) | ranges::to<std::vector>();
  EXPECT_TRUE(processed.empty());
}

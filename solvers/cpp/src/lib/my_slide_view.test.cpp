#define TEST_MY_SLIDE_VIEW
#include "my_slide_view.hpp"

#include <gtest/gtest.h>

#include <ranges>
#include <span>
#include <string>

#if defined(_LIBCPP_VERSION) && __cpp_lib_ranges_slide >= 202202L
#error "libc++ started supporting std::views::slide. Use it directly"
#endif

namespace ranges = std::ranges;
namespace views = std::views;

using Sliced = std::vector<std::string>;

TEST(MySlideView, BetweenPipes) {
  const std::string data{"123456789"};
  auto processed =
    data | views::drop(1) | MySlide(3) | views::take(4) | ranges::to<Sliced>();
  ASSERT_EQ(processed.size(), 4);
  EXPECT_EQ(processed[0], "234");
  EXPECT_EQ(processed[1], "345");
  EXPECT_EQ(processed[2], "456");
  EXPECT_EQ(processed[3], "567");
}

TEST(MySlideView, EmptyData) {
  const std::string empty;
  auto processed = empty | MySlide(2) | ranges::to<std::vector>();
  EXPECT_TRUE(processed.empty());
}

TEST(MySlideView, EqualSize) {
  const std::string one{"1"};
  auto processed = one | MySlide(1) | ranges::to<Sliced>();
  ASSERT_EQ(processed.size(), 1);
  EXPECT_EQ(processed[0], "1");
}

TEST(MySlideView, LastIncluded) {
  const std::string data{"12345"};
  auto processed = data | MySlide(2) | ranges::to<Sliced>();
  ASSERT_EQ(processed.size(), 4);
  EXPECT_EQ(processed[0], "12");
  EXPECT_EQ(processed[1], "23");
  EXPECT_EQ(processed[2], "34");
  EXPECT_EQ(processed[3], "45");
}

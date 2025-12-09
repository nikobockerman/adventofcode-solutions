#define TEST_MY_ENUMERATE_VIEW
#include "my_enumerate_view.hpp"

#include <gtest/gtest.h>

#include <ranges>
#include <span>
#include <string>
#include <tuple>

#if defined(_LIBCPP_VERSION) && __cpp_lib_ranges_enumerate >= 202302L
#error "libc++ started supporting std::views::enumerate. Use it directly"
#endif

namespace ranges = std::ranges;
namespace views = std::views;

using Tuple = std::tuple<size_t, char>;
using Enumerated = std::vector<Tuple>;

namespace {

template <typename T>
auto r(size_t i, T&& v) {
  return std::make_tuple<size_t, T>(std::move(i), std::forward<T>(v));
}

}  // namespace

TEST(MyEnumerateView, BetweenPipes) {
  const std::string data{"123456789"};
  auto processed = data | views::drop(1) | MyEnumerate | views::take(4) |
                   ranges::to<Enumerated>();
  ASSERT_EQ(processed.size(), 4);
  EXPECT_EQ(processed[0], r(0, '2'));
  EXPECT_EQ(processed[1], r(1, '3'));
  EXPECT_EQ(processed[2], r(2, '4'));
  EXPECT_EQ(processed[3], r(3, '5'));
}

TEST(MyEnumerateView, EmptyData) {
  const std::string empty;
  auto processed = empty | MyEnumerate | ranges::to<Enumerated>();
  EXPECT_TRUE(processed.empty());
}

TEST(MyEnumerateView, EqualSize) {
  const std::string one{"1"};
  auto processed = one | MyEnumerate | ranges::to<Enumerated>();
  ASSERT_EQ(processed.size(), 1);
  EXPECT_EQ(processed[0], r(0, '1'));
}

TEST(MyEnumerateView, LastIncluded) {
  const std::string data{"12345"};
  auto processed = data | MyEnumerate | ranges::to<Enumerated>();
  ASSERT_EQ(processed.size(), 5);
  EXPECT_EQ(processed[0], r(0, '1'));
  EXPECT_EQ(processed[1], r(1, '2'));
  EXPECT_EQ(processed[2], r(2, '3'));
  EXPECT_EQ(processed[3], r(3, '4'));
  EXPECT_EQ(processed[4], r(4, '5'));
}

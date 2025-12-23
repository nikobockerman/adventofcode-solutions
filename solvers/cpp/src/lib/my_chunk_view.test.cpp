#define TEST_MY_CHUNK_VIEW
#include "my_chunk_view.hpp"

#include <gtest/gtest.h>

#include <ranges>
#include <span>
#include <string>
#include <tuple>

#if defined(_LIBCPP_VERSION) && __cpp_lib_ranges_chunk >= 202202L
#error "libc++ started supporting std::views::chunk. Use it directly"
#endif

namespace ranges = std::ranges;
namespace views = std::views;

using Chunked = std::vector<std::string>;

TEST(MyChunkView, BetweenPipes) {
  const std::string data{"123456789"};
  auto processed =
    data | views::drop(1) | MyChunk(3) | views::take(2) | ranges::to<Chunked>();
  ASSERT_EQ(processed.size(), 2);
  EXPECT_EQ(processed[0], "234");
  EXPECT_EQ(processed[1], "567");
}

TEST(MyChunkView, EmptyData) {
  const std::string empty;
  auto processed = empty | MyChunk(2) | ranges::to<std::vector>();
  EXPECT_TRUE(processed.empty());
}

TEST(MyChunkView, EqualSize) {
  const std::string one{"123"};
  auto processed = one | MyChunk(3) | ranges::to<Chunked>();
  ASSERT_EQ(processed.size(), 1);
  EXPECT_EQ(processed[0], "123");
}

TEST(MyChunkView, LargerThanInput) {
  const std::string data{"12345"};
  auto processed = data | MyChunk(4) | ranges::to<Chunked>();
  ASSERT_EQ(processed.size(), 2);
  EXPECT_EQ(processed[0], "1234");
  EXPECT_EQ(processed[1], "5");
}

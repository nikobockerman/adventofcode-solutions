#include "my_chunk_view.hpp"
#include "my_fold_left_first.hpp"
#include "solver.hpp"
#include "utils.hpp"

#include <spdlog/spdlog.h>

#include <convert.hpp>

namespace ranges = std::ranges;
namespace views = std::views;

namespace {

class Id final {
 public:
  explicit Id(uint64_t id) : _id(id), _idStr(std::to_string(id)) {}

  [[nodiscard]] auto id() const { return _id; }
  [[nodiscard]] auto idStr() const -> const std::string& { return _idStr; }

 private:
  uint64_t _id;
  std::string _idStr;
};

auto rangesLine(const std::string_view inputStr) {
  auto lines = splitLinesUntilEmpty(inputStr) | ranges::to<std::vector>();
  if (lines.size() != 1) {
    throw std::runtime_error("Expected only one line of input");
  }
  return lines.at(0);
}

auto solve(const std::string_view inputStr, auto&& filterIds) {
  auto line = rangesLine(inputStr);
  return MyFoldLeftFirst(
           line | views::split(',') |
             views::transform([filterIds](auto&& idRange) {
               auto parts =
                 idRange | views::split('-') | ranges::to<std::vector>();
               auto start = convert<uint64_t>(parts.at(0));
               auto end = convert<uint64_t>(parts.at(1));
               spdlog::debug("Checking range [{}, {}]", start, end);
               auto ids =
                 filterIds(views::iota(start, end + 1) |
                           views::transform([](auto id) { return Id(id); }));
               return MyFoldLeftFirst(ids | views::transform([](const Id& id) {
                                        spdlog::debug("Found invalid ID: {}",
                                                      id.idStr());
                                        return id.id();
                                      }),
                                      std::plus{})
                 .value_or(uint64_t{});
             }),
           std::plus{})
    .value_or(uint64_t{});
}

}  // namespace

auto solver::p1(const std::string_view inputStr) -> Answer {
  return solve(inputStr, [](auto&& ids) {
    return ids | views::filter([](const Id& id) {
             return id.idStr().length() % 2 == 0;
           }) |
           views::filter([](const Id& id) {
             auto view = std::string_view(id.idStr());
             return view.substr(0, view.length() / 2) ==
                    view.substr(view.length() / 2);
           });
  });
}

auto solver::p2(const std::string_view inputStr) -> Answer {
  return solve(inputStr, [](auto&& ids) {
    return ids | views::filter([](const Id& id) {
             auto view = std::string_view(id.idStr());
             for (auto length : views::iota(std::size_t{1}, view.size())) {
               if (view.size() % length != 0) {
                 continue;
               }
               auto value = view.substr(0, length);
               auto nonMatching =
                 view | MyChunk(length) | views::drop(1) |
                 views::transform(
                   [](auto&& part) { return std::string_view(part); }) |
                 views::filter([value](auto&& part) { return part != value; });

               if (ranges::empty(nonMatching)) {
                 return true;
               }
             }
             return false;
           });
  });
}

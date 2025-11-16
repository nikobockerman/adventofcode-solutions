#pragma once

#include <cstdint>
#include <format>
#include <string>
#include <variant>

using AnswerVariant = std::variant<uint64_t, int64_t, std::string>;

class Answer : public AnswerVariant {
 public:
  using AnswerVariant::variant;
};

template <>
struct std::formatter<Answer> {
  template <typename ParseContext>
  constexpr auto parse(ParseContext& ctx) const {
    return ctx.begin();
  }

  template <typename FormatContext>
  auto format(const Answer& result, FormatContext& ctx) const {
    if (std::holds_alternative<uint64_t>(result)) {
      return std::format_to(ctx.out(), "{}", std::get<uint64_t>(result));
    }
    if (std::holds_alternative<int64_t>(result)) {
      return std::format_to(ctx.out(), "{}", std::get<int64_t>(result));
    }
    if (std::holds_alternative<std::string>(result)) {
      return std::format_to(ctx.out(), "{}", std::get<std::string>(result));
    }
    throw std::runtime_error("Unknown result type");
  }
};

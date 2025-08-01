#include "solver.hpp"

#include <fmt/base.h>
#include <spdlog/common.h>
#include <spdlog/sinks/stdout_color_sinks.h>
#include <spdlog/spdlog.h>

#include <array>
#include <charconv>
#include <cstdint>
#include <cstdlib>
#include <format>
#include <iostream>
#include <span>
#include <stdexcept>
#include <string>
#include <string_view>
#include <system_error>

namespace {

enum class Part : std::uint8_t {
  P1,
  P2,
};

auto argToInt(std::string_view arg) -> std::uint8_t {
  std::uint8_t value = 0;
  const auto *last = arg.data() + arg.size();
  if (auto [ptr,
            ec]{std::from_chars(arg.data(), arg.data() + arg.size(), value)};
      ec != std::errc() || ptr != last) {
    throw std::runtime_error(std::format("Invalid argument: {}", arg));
  }
  return value;
}

auto processArgs(const std::span<const char *> args) {
  if (args.size() != 3) {
    throw std::runtime_error(
      std::format("Invalid number of arguments: {}", args.size()));
  }
  auto verbosity = argToInt(args[1]);
  auto part = argToInt(args[2]);

  if (verbosity > 2) {
    throw std::runtime_error(
      std::format("Invalid verbosity level: {}", verbosity));
  }

  if (part < 1 || part > 2) {
    throw std::runtime_error(std::format("Invalid part: {}", part));
  }

  const auto level =
    std::array{spdlog::level::warn, spdlog::level::info, spdlog::level::debug}
      .at(verbosity);
  spdlog::set_level(level);

  return std::array{Part::P1, Part::P2}.at(part - 1);
}

auto run(const std::span<const char *> &args) -> int {
  const auto part = processArgs(args);

  auto stderr_logger = spdlog::stderr_color_mt("stderr");
  spdlog::set_default_logger(stderr_logger);

  std::string inputStr;
  while (true) {
    constexpr std::size_t batchSize = 1'000;
    std::string inputBatch(batchSize, '\0');
    std::cin.read(inputBatch.data(), batchSize);

    const auto readSize = std::cin.gcount();
    inputStr.append(inputBatch.begin(), inputBatch.begin() + readSize);
    if (std::cin.eof()) {
      break;
    }
  }

  auto answer = part == Part::P1 ? solver::p1(inputStr) : solver::p2(inputStr);
  fmt::print("{}\n", answer);

  return 0;
}

}  // namespace

// NOLINTNEXTLINE(bugprone-exception-escape)
auto main(const int argc, const char *argv[]) -> int {
  return run(std::span(argv, argc));
}

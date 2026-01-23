# Advent of Code C++ Solutions

## Build Systems

This project supports two build systems:
- **CMake + Conan** (existing)
- **Bazel** (new)

Both follow the same configuration philosophy: committed files specify only minimum requirements, while user-controlled local files define compilers, build types, and flags.

## Bazel Build

### Prerequisites

- Bazel 6.0+ (`brew install bazel`)

### Quick Start

```bash
# Copy and customize local configuration
cp .bazelrc.local.example .bazelrc.local
# Edit .bazelrc.local to set compiler paths and preferences

# Build a solver
bazel build //src/bin:y2022_d01

# Run tests
bazel test //...

# Run a solver
bazel run //src/bin:y2022_d01
```

### Configuration Philosophy

| Committed | Local (`.bazelrc.local`) |
|-----------|--------------------------|
| C++ standard (23) | Compiler paths |
| Bzlmod enabled | C++ stdlib choice |
| Dependencies | Build types (dbg/opt) |
| | Warning flags |
| | Sanitizers |
| | clang-tidy |

### File Structure

```
solvers/cpp/
├── MODULE.bazel             # Dependencies
├── WORKSPACE                # Workspace name
├── .bazelrc                 # Minimal: C++ standard, bzlmod
├── .bazelrc.local.example   # User configuration template
├── .bazelrc.local           # Your local config (not committed)
├── src/
│   ├── lib/BUILD.bazel      # Library targets
│   ├── bin/BUILD.bazel      # Solver executables and tests
│   └── test_utils/BUILD.bazel
└── ...
```

### Build Commands

```bash
# With configurations from .bazelrc.local:
bazel build --config=clang-libcxx-dbg //src/bin:y2022_d01
bazel build --config=gcc-opt //src/bin:all
bazel build --config=clang-libcxx-sanitizers //src/bin:y2022_d01

# Run specific test
bazel test //src/bin:y2022_d01_test

# Run library tests
bazel test //src/lib:lib_test
```

## CMake + Conan Build

See `CMakePresets.json` for committed configuration and use `CMakeUserPresets.json` for local settings.

```bash
cmake --preset=<your-preset>
cmake --build build/<preset>
ctest --test-dir build/<preset>
```

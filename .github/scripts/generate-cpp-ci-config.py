#!/usr/bin/env python3
"""Generate concrete C++ CI configuration for one workflow matrix entry."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import sys
from pathlib import Path
from typing import Final

_REPOSITORY_ROOT: Final = Path(__file__).resolve().parents[2]
_CPP_DIR: Final = _REPOSITORY_ROOT / "solvers" / "cpp"


class ConfigurationError(ValueError):
    """Raised when a matrix entry cannot be represented by the CI configuration."""


class MissingEnvironmentError(ConfigurationError):
    """Raised when a generated configuration needs an unavailable environment value."""

    def __init__(self, name: str) -> None:
        super().__init__(f"Required environment variable is not set: {name}")


class UnsupportedMatrixError(ConfigurationError):
    """Raised when the workflow matrix specifies an unsupported build."""

    def __init__(self, matrix: tuple[str, str, str, str]) -> None:
        super().__init__(f"Unsupported C++ CI matrix entry: {', '.join(matrix)}")


def _required_environment(name: str) -> str:
    value = os.environ.get(name)
    if value:
        return value
    raise MissingEnvironmentError(name)


def _validate_matrix(args: argparse.Namespace) -> None:
    valid = {
        ("ubuntu", "clang", "libc++", "debug"),
        ("ubuntu", "clang", "libc++", "release"),
        ("ubuntu", "clang", "libc++", "sanitizers"),
        ("ubuntu", "clang", "libc++", "hardened"),
        ("ubuntu", "clang", "libstdc++", "debug"),
        ("ubuntu", "clang", "libstdc++", "release"),
        ("ubuntu", "gcc", "libstdc++", "debug"),
        ("ubuntu", "gcc", "libstdc++", "release"),
        ("macos", "clang", "libstdc++", "release"),
    }
    matrix = (args.os, args.compiler, args.cxx_lib, args.build_type)
    if matrix not in valid:
        raise UnsupportedMatrixError(matrix)


def _profile_path() -> str:
    # sourceDir is resolved by CMake, not from the process environment.
    return "auto-cmake;${sourceDir}/conan-profile-ci"


def _add_clang_compilers(cache_variables: dict[str, str], llvm_prefix: str) -> None:
    cache_variables.update(
        {
            "CMAKE_C_COMPILER": f"{llvm_prefix}/bin/clang",
            "CMAKE_CXX_COMPILER": f"{llvm_prefix}/bin/clang++",
        }
    )


def _native_gcc_configuration(
    cache_variables: dict[str, str], homebrew_prefix: str, flags: list[str]
) -> tuple[dict[str, str], str]:
    gcc_major_version = _required_environment("GCC_MAJOR_VERSION")
    gcc_prefix = f"{homebrew_prefix}/opt/gcc@{gcc_major_version}"
    cache_variables.update(
        {
            "CMAKE_C_COMPILER": f"{gcc_prefix}/bin/gcc-{gcc_major_version}",
            "CMAKE_CXX_COMPILER": f"{gcc_prefix}/bin/g++-{gcc_major_version}",
            "CMAKE_CXX_FLAGS": " ".join(flags),
        }
    )
    profile = (
        "# Native GCC uses Conan's auto-detected profile; no add-on is required.\n"
    )
    return cache_variables, profile


def _hardened_libcxx_configuration(
    cache_variables: dict[str, str], homebrew_prefix: str, flags: list[str]
) -> tuple[dict[str, str], str]:
    llvm_major_version = _required_environment("LLVM_MAJOR_VERSION")
    llvm_prefix = f"{homebrew_prefix}/opt/llvm@{llvm_major_version}"
    hardened_libcxx_dir = _required_environment("HARDENED_LIBCXX_DIR")
    _add_clang_compilers(cache_variables, llvm_prefix)
    cmake_linker_flags = " ".join(
        [
            "-stdlib=libc++",
            f"-L{hardened_libcxx_dir}/lib",
            "-lunwind",
            f"-Wl,-rpath,{hardened_libcxx_dir}/lib",
        ]
    )
    conan_linker_flags = ", ".join(
        [
            "'-stdlib=libc++'",
            f"'-L{hardened_libcxx_dir}/lib'",
            "'-lunwind'",
        ]
    )

    cache_variables.update(
        {
            "CMAKE_CXX_FLAGS": " ".join(
                [
                    "-D_LIBCPP_DEBUG=1",
                    "-D_LIBCPP_HARDENING_MODE=_LIBCPP_HARDENING_MODE_DEBUG",
                    *flags,
                    f"-stdlib++-isystem{hardened_libcxx_dir}/include/c++/v1",
                ]
            ),
            "CMAKE_EXE_LINKER_FLAGS": cmake_linker_flags,
            "CMAKE_SHARED_LINKER_FLAGS": cmake_linker_flags,
            "CONAN_HOST_PROFILE": _profile_path(),
        }
    )
    profile = "\n".join(
        [
            "[conf]",
            (
                "tools.build:cxxflags=['-stdlib++-isystem"
                f"{hardened_libcxx_dir}/include/c++/v1', "
                "'-D_LIBCPP_DEBUG=1', "
                "'-D_LIBCPP_HARDENING_MODE=_LIBCPP_HARDENING_MODE_DEBUG']"
            ),
            f"tools.build:exelinkflags=[{conan_linker_flags}]",
            f"tools.build:sharedlinkflags=[{conan_linker_flags}]",
            "",
        ]
    )
    return cache_variables, profile


def _clang_libcxx_configuration(
    cache_variables: dict[str, str],
    homebrew_prefix: str,
    flags: list[str],
    os_name: str,
    *,
    sanitizers: bool,
) -> tuple[dict[str, str], str]:
    llvm_major_version = _required_environment("LLVM_MAJOR_VERSION")
    llvm_prefix = f"{homebrew_prefix}/opt/llvm@{llvm_major_version}"
    libcxx_flags = f"-stdlib++-isystem{llvm_prefix}/include/c++/v1"
    cmake_linker_flags = " ".join(
        [
            "-stdlib=libc++",
            f"-L{llvm_prefix}/lib",
            f"-Wl,-rpath,{llvm_prefix}/lib",
        ]
    )
    cxx_flags = [*flags, libcxx_flags]
    if sanitizers:
        cxx_flags = [
            "-O1",
            "-fsanitize=address,undefined",
            "-fno-sanitize-recover=all",
            "-fno-omit-frame-pointer",
            "-fno-optimize-sibling-calls",
            "-fno-sanitize-merge",
            *cxx_flags,
        ]
        cmake_linker_flags = f"-fsanitize=address,undefined {cmake_linker_flags}"

    _add_clang_compilers(cache_variables, llvm_prefix)
    cache_variables.update(
        {
            "CMAKE_CXX_FLAGS": " ".join(cxx_flags),
            "CMAKE_EXE_LINKER_FLAGS": cmake_linker_flags,
            "CMAKE_SHARED_LINKER_FLAGS": cmake_linker_flags,
            "CONAN_HOST_PROFILE": _profile_path(),
        }
    )
    if not sanitizers:
        cache_variables["CMAKE_CXX_CLANG_TIDY"] = f"{llvm_prefix}/bin/clang-tidy"

    profile_library_dir = (
        f"{llvm_prefix}/lib/c++" if os_name == "macos" else f"{llvm_prefix}/lib"
    )
    conan_linker_flags = ", ".join(
        [
            '"-stdlib=libc++"',
            f'"-L{profile_library_dir}"',
        ]
    )
    profile_lines = [
        "[conf]",
        f'tools.build:cxxflags=["{libcxx_flags}"]',
        f"tools.build:exelinkflags=[{conan_linker_flags}]",
        f"tools.build:sharedlinkflags=[{conan_linker_flags}]",
    ]
    if sanitizers:
        llvm_full_version = _required_environment("LLVM_FULL_VERSION")
        profile_lines = [
            "[settings]",
            f"compiler.abi_extra=sanitizers-{llvm_full_version}",
            "",
            *profile_lines,
        ]
    return cache_variables, "\n".join([*profile_lines, ""])


def _clang_libstdcxx_configuration(
    cache_variables: dict[str, str],
    homebrew_prefix: str,
    flags: list[str],
    os_name: str,
) -> tuple[dict[str, str], str]:
    gcc_major_version = _required_environment("GCC_MAJOR_VERSION")
    llvm_major_version = _required_environment("LLVM_MAJOR_VERSION")
    gcc_prefix = f"{homebrew_prefix}/opt/gcc@{gcc_major_version}"
    llvm_prefix = f"{homebrew_prefix}/opt/llvm@{llvm_major_version}"
    target = "aarch64-apple-darwin24" if os_name == "macos" else "x86_64-pc-linux-gnu"
    _add_clang_compilers(cache_variables, llvm_prefix)
    cmake_linker_flags = " ".join(
        [
            "-stdlib=libstdc++",
            f"-L{gcc_prefix}/lib/gcc/{gcc_major_version}",
            f"-Wl,-rpath,{gcc_prefix}/lib/gcc/{gcc_major_version}",
        ]
    )
    conan_linker_flags = ", ".join(
        [
            '"-stdlib=libstdc++"',
            f'"-L{gcc_prefix}/lib/gcc/{gcc_major_version}"',
        ]
    )

    cache_variables.update(
        {
            "CMAKE_CXX_FLAGS": " ".join(
                [
                    *flags,
                    f"-stdlib++-isystem{gcc_prefix}/include/c++/{gcc_major_version}",
                    f"-cxx-isystem{gcc_prefix}/include/c++/{gcc_major_version}/{target}",
                ]
            ),
            "CMAKE_EXE_LINKER_FLAGS": cmake_linker_flags,
            "CMAKE_SHARED_LINKER_FLAGS": cmake_linker_flags,
            "CONAN_HOST_PROFILE": _profile_path(),
            "CMAKE_CXX_CLANG_TIDY": f"{llvm_prefix}/bin/clang-tidy",
        }
    )
    profile = "\n".join(
        [
            "[settings]",
            f"compiler.abi_extra=libstdc++-gcc-{gcc_major_version}",
            "",
            "[conf]",
            (
                "tools.build:cxxflags=["
                f'"-stdlib++-isystem{gcc_prefix}/include/c++/{gcc_major_version}", '
                f'"-cxx-isystem{gcc_prefix}/include/c++/{gcc_major_version}/{target}"]'
            ),
            f"tools.build:exelinkflags=[{conan_linker_flags}]",
            f"tools.build:sharedlinkflags=[{conan_linker_flags}]",
            "",
        ]
    )
    return cache_variables, profile


def _configuration(args: argparse.Namespace) -> tuple[dict[str, str], str]:
    homebrew_prefix = _required_environment("HOMEBREW_PREFIX")
    flags = ["-Wall", "-Wextra", "-Werror"]
    cache_variables: dict[str, str] = {
        "CMAKE_BUILD_TYPE": "Release" if args.build_type == "release" else "Debug",
    }

    match args.compiler, args.cxx_lib, args.build_type:
        case "gcc", "libstdc++", "debug" | "release":
            return _native_gcc_configuration(cache_variables, homebrew_prefix, flags)
        case "clang", "libc++", "hardened":
            return _hardened_libcxx_configuration(
                cache_variables, homebrew_prefix, flags
            )
        case "clang", "libc++", "sanitizers":
            return _clang_libcxx_configuration(
                cache_variables,
                homebrew_prefix,
                flags,
                args.os,
                sanitizers=True,
            )
        case "clang", "libc++", "debug" | "release":
            return _clang_libcxx_configuration(
                cache_variables,
                homebrew_prefix,
                flags,
                args.os,
                sanitizers=False,
            )
        case "clang", "libstdc++", "debug" | "release":
            return _clang_libstdcxx_configuration(
                cache_variables, homebrew_prefix, flags, args.os
            )
        case _:
            raise AssertionError(
                (args.os, args.compiler, args.cxx_lib, args.build_type)
            )


def _write_environment(path: Path, args: argparse.Namespace) -> None:
    lines = [
        "# Generated by .github/scripts/generate-cpp-ci-config.py.",
        f"# Matrix: {args.os} {args.compiler} {args.cxx_lib} {args.build_type}.",
    ]
    if args.build_type == "sanitizers":
        lines.extend(
            [
                f"export ASAN_OPTIONS={shlex.quote('detect_leaks=1')}",
                f"export UBSAN_OPTIONS={shlex.quote('print_stacktrace=1')}",
            ]
        )
    else:
        lines.append(
            "# This matrix does not need additional runtime environment variables."
        )
    path.write_text("\n".join([*lines, ""]), encoding="utf-8")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--os", choices=("ubuntu", "macos"), required=True)
    parser.add_argument("--compiler", choices=("clang", "gcc"), required=True)
    parser.add_argument("--cxx-lib", choices=("libc++", "libstdc++"), required=True)
    parser.add_argument(
        "--build-type",
        choices=("debug", "release", "sanitizers", "hardened"),
        required=True,
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        _validate_matrix(args)
        cache_variables, conan_profile = _configuration(args)
    except ConfigurationError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    preset = {
        "version": 8,
        "configurePresets": [
            {
                "name": "ci",
                "binaryDir": "build",
                "inherits": ["cmake-conan", "sccache", "ninja"],
                "cacheVariables": cache_variables,
            }
        ],
    }
    (_CPP_DIR / "CMakeUserPresets.json").write_text(
        json.dumps(preset, indent=2) + "\n", encoding="utf-8"
    )
    _write_environment(_CPP_DIR / "ci.env", args)
    (_CPP_DIR / "conan-profile-ci").write_text(conan_profile, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

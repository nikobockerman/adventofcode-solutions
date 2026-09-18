#!/usr/bin/env python3
"""Generate the C++ CI build matrix and the configuration for one matrix entry."""

from __future__ import annotations

import argparse
import functools
import json
import os
import re
import shlex
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal, get_args

_REPOSITORY_ROOT: Final = Path(__file__).resolve().parents[2]
_CPP_DIR: Final = _REPOSITORY_ROOT / "solvers" / "cpp"

_GLIBCXX_DEBUG_FLAGS: Final = ("-D_GLIBCXX_DEBUG", "-D_GLIBCXX_DEBUG_PEDANTIC")

type _OS = Literal["macos", "ubuntu"]
type _Compiler = Literal["clang", "gcc"]
type _CxxLib = Literal["libc++", "libstdc++"]
type _BuildType = Literal["debug", "release", "sanitizers", "hardened"]


# Runner image hosting each operating system.
@functools.cache
def _runners() -> dict[_OS, str]:
    return {"macos": "macos-15", "ubuntu": "ubuntu-24.04"}


# Every scenario CI builds. The workflow obtains its job list from the `matrix`
# subcommand rather than declaring one, so this table is the only place the set of
# scenarios is written down and the two cannot drift apart.
@functools.cache
def _matrix() -> tuple[_MatrixEntry, ...]:
    return (
        _MatrixEntry("ubuntu", "clang", "libc++", "debug"),
        _MatrixEntry("ubuntu", "clang", "libc++", "release"),
        _MatrixEntry("ubuntu", "clang", "libc++", "sanitizers"),
        _MatrixEntry("ubuntu", "clang", "libc++", "hardened"),
        _MatrixEntry("ubuntu", "clang", "libstdc++", "debug"),
        _MatrixEntry("ubuntu", "clang", "libstdc++", "release"),
        _MatrixEntry("ubuntu", "gcc", "libstdc++", "debug"),
        _MatrixEntry("ubuntu", "gcc", "libstdc++", "release"),
        _MatrixEntry("macos", "clang", "libstdc++", "release"),
    )


@dataclass(frozen=True)
class _MatrixEntry:
    """One C++ build scenario: which compiler, standard library and build type."""

    os: _OS
    compiler: _Compiler
    cxx_lib: _CxxLib
    build_type: _BuildType

    @property
    def run_id(self) -> str:
        return f"{self.os}-{self.compiler}-{self.cxx_lib}-{self.build_type}"

    def __str__(self) -> str:
        return self.run_id


@dataclass(frozen=True)
class _ConanProfile:
    """The Conan profile add-on layered on the auto-detected profile.

    Every field is what the profile *means*; `_render_profile` decides how it is
    spelled, so all matrix entries produce the same shape of file.
    """

    cxxflags: tuple[str, ...] = ()
    # Conan has no combined link-flags conf; the same list feeds exe and shared.
    linkflags: tuple[str, ...] = ()
    # Not a build flag: an opaque discriminator for toolchain identity that the
    # flags themselves do not spell out.
    abi_tag: str = ""

    def __bool__(self) -> bool:
        return any((self.cxxflags, self.linkflags, self.abi_tag))


class _ConfigurationError(ValueError):
    """Raised when a matrix entry cannot be represented by the CI configuration."""


class _MissingEnvironmentError(_ConfigurationError):
    """Raised when a generated configuration needs an unavailable environment value."""

    def __init__(self, name: str) -> None:
        super().__init__(f"Required environment variable is not set: {name}")


class _UnsupportedMatrixError(_ConfigurationError):
    """Raised when the workflow matrix specifies an unsupported build."""

    def __init__(self, matrix: _MatrixEntry) -> None:
        super().__init__(f"Unsupported C++ CI matrix entry: {matrix}")


def _required_environment(name: str) -> str:
    value = os.environ.get(name)
    if value:
        return value
    raise _MissingEnvironmentError(name)


def _parse_matrix(args: argparse.Namespace) -> _MatrixEntry:
    matrix = _MatrixEntry(args.os, args.compiler, args.cxx_lib, args.build_type)
    if matrix not in _matrix():
        raise _UnsupportedMatrixError(matrix)
    return matrix


def _github_include(
    entry: _MatrixEntry, homebrew_hashes: dict[_OS, str]
) -> dict[str, str]:
    return {
        "os": entry.os,
        "compiler": entry.compiler,
        "cxxLib": entry.cxx_lib,
        "buildType": entry.build_type,
        "runId": entry.run_id,
        "runsOn": _runners()[entry.os],
        "homebrew-downloads-hash-from-prepare": homebrew_hashes[entry.os],
    }


def _profile_path() -> str:
    # sourceDir is resolved by CMake, not from the process environment.
    return "auto-cmake;${sourceDir}/conan-profile-ci"


type _ConanConfValue = str | tuple[str, ...]


def _conan_conf_entries(profile: _ConanProfile) -> list[tuple[str, _ConanConfValue]]:
    entries: list[tuple[str, _ConanConfValue]] = []
    if profile.abi_tag:
        entries.append(("user.aoc:abi", profile.abi_tag))
    if profile.cxxflags:
        entries.append(("tools.build:cxxflags", profile.cxxflags))
    if profile.linkflags:
        entries.append(("tools.build:exelinkflags", profile.linkflags))
        entries.append(("tools.build:sharedlinkflags", profile.linkflags))
    return entries


def _render_conan_profile(profile: _ConanProfile) -> str:
    entries = _conan_conf_entries(profile)
    if not entries:
        return "# This matrix entry needs no add-on to the auto-detected profile.\n"

    patterns = '", "'.join(re.escape(name) for name, _ in entries)
    lines = [
        "[conf]",
        f'tools.info.package_id:confs=["{patterns}"]',
        *(f"{name}={json.dumps(value)}" for name, value in entries),
    ]
    return "\n".join([*lines, ""])


def _add_clang_compilers(cache_variables: dict[str, str], llvm_prefix: str) -> None:
    cache_variables.update(
        {
            "CMAKE_C_COMPILER": f"{llvm_prefix}/bin/clang",
            "CMAKE_CXX_COMPILER": f"{llvm_prefix}/bin/clang++",
        }
    )


def _native_gcc_configuration(
    cache_variables: dict[str, str],
    homebrew_prefix: str,
    flags: list[str],
    *,
    glibcxx_debug: bool,
) -> tuple[dict[str, str], _ConanProfile]:
    gcc_major_version = _required_environment("GCC_MAJOR_VERSION")
    gcc_prefix = f"{homebrew_prefix}/opt/gcc@{gcc_major_version}"
    debug_flags = _GLIBCXX_DEBUG_FLAGS if glibcxx_debug else ()
    cache_variables.update(
        {
            "CMAKE_C_COMPILER": f"{gcc_prefix}/bin/gcc-{gcc_major_version}",
            "CMAKE_CXX_COMPILER": f"{gcc_prefix}/bin/g++-{gcc_major_version}",
            "CMAKE_CXX_FLAGS": " ".join([*debug_flags, *flags]),
        }
    )
    # With no macros the add-on is empty, which builds dependencies exactly as
    # Conan detects them.
    return cache_variables, _ConanProfile(cxxflags=debug_flags)


def _hardened_libcxx_configuration(
    cache_variables: dict[str, str], homebrew_prefix: str, flags: list[str]
) -> tuple[dict[str, str], _ConanProfile]:
    llvm_major_version = _required_environment("LLVM_MAJOR_VERSION")
    llvm_prefix = f"{homebrew_prefix}/opt/llvm@{llvm_major_version}"
    hardened_abi_tag = _required_environment("HARDENED_ABI_TAG")
    hardened_libcxx_dir = _required_environment("HARDENED_LIBCXX_DIR")
    _add_clang_compilers(cache_variables, llvm_prefix)
    libcxx_flags = f"-stdlib++-isystem{hardened_libcxx_dir}/include/c++/v1"
    hardening_flags = (
        "-D_LIBCPP_DEBUG=1",
        "-D_LIBCPP_HARDENING_MODE=_LIBCPP_HARDENING_MODE_DEBUG",
    )
    conan_linker_flags = (
        "-stdlib=libc++",
        f"-L{hardened_libcxx_dir}/lib",
        "-lunwind",
    )
    # Dependencies are found through the Conan-generated CMake config, so only
    # the application needs the runtime search path baked in.
    cmake_linker_flags = " ".join(
        [*conan_linker_flags, f"-Wl,-rpath,{hardened_libcxx_dir}/lib"]
    )

    cache_variables.update(
        {
            "CMAKE_CXX_FLAGS": " ".join([*hardening_flags, *flags, libcxx_flags]),
            "CMAKE_EXE_LINKER_FLAGS": cmake_linker_flags,
            "CMAKE_SHARED_LINKER_FLAGS": cmake_linker_flags,
        }
    )
    # The hardened libc++ installs to a fixed path, so every flag above stays
    # identical when a new one is built there. The tag is the only thing that
    # separates dependencies built against one libc++ from another; its value is
    # that build's cache key, so the two decisions cannot drift apart.
    profile = _ConanProfile(
        abi_tag=hardened_abi_tag,
        cxxflags=(libcxx_flags, *hardening_flags),
        linkflags=conan_linker_flags,
    )
    return cache_variables, profile


def _clang_libcxx_configuration(
    cache_variables: dict[str, str],
    homebrew_prefix: str,
    flags: list[str],
    os_name: str,
    *,
    sanitizers: bool,
) -> tuple[dict[str, str], _ConanProfile]:
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
        }
    )
    if not sanitizers:
        cache_variables["CMAKE_CXX_CLANG_TIDY"] = f"{llvm_prefix}/bin/clang-tidy"

    profile_library_dir = (
        f"{llvm_prefix}/lib/c++" if os_name == "macos" else f"{llvm_prefix}/lib"
    )
    # The sanitizer flags stay out of the profile: dependencies are built without
    # sanitizers, so no flag separates them from a plain libc++ build. They still
    # must not outlive this exact LLVM, whose libc++ and ASan runtime the
    # application links against — only its major version reaches the flags above.
    abi_tag = f"llvm-{_required_environment('LLVM_FULL_VERSION')}" if sanitizers else ""
    profile = _ConanProfile(
        abi_tag=abi_tag,
        cxxflags=(libcxx_flags,),
        linkflags=("-stdlib=libc++", f"-L{profile_library_dir}"),
    )
    return cache_variables, profile


def _clang_libstdcxx_configuration(
    cache_variables: dict[str, str],
    homebrew_prefix: str,
    flags: list[str],
    os_name: str,
) -> tuple[dict[str, str], _ConanProfile]:
    gcc_major_version = _required_environment("GCC_MAJOR_VERSION")
    llvm_major_version = _required_environment("LLVM_MAJOR_VERSION")
    gcc_prefix = f"{homebrew_prefix}/opt/gcc@{gcc_major_version}"
    llvm_prefix = f"{homebrew_prefix}/opt/llvm@{llvm_major_version}"
    target = "aarch64-apple-darwin24" if os_name == "macos" else "x86_64-pc-linux-gnu"
    _add_clang_compilers(cache_variables, llvm_prefix)
    libstdcxx_flags = (
        f"-stdlib++-isystem{gcc_prefix}/include/c++/{gcc_major_version}",
        f"-cxx-isystem{gcc_prefix}/include/c++/{gcc_major_version}/{target}",
    )
    conan_linker_flags = (
        "-stdlib=libstdc++",
        f"-L{gcc_prefix}/lib/gcc/{gcc_major_version}",
    )
    # Dependencies are found through the Conan-generated CMake config, so only
    # the application needs the runtime search path baked in.
    cmake_linker_flags = " ".join(
        [*conan_linker_flags, f"-Wl,-rpath,{gcc_prefix}/lib/gcc/{gcc_major_version}"]
    )

    cache_variables.update(
        {
            "CMAKE_CXX_FLAGS": " ".join([*flags, *libstdcxx_flags]),
            "CMAKE_EXE_LINKER_FLAGS": cmake_linker_flags,
            "CMAKE_SHARED_LINKER_FLAGS": cmake_linker_flags,
            "CMAKE_CXX_CLANG_TIDY": f"{llvm_prefix}/bin/clang-tidy",
        }
    )
    profile = _ConanProfile(
        cxxflags=libstdcxx_flags,
        linkflags=conan_linker_flags,
    )
    return cache_variables, profile


def _toolchain_configuration(
    entry: _MatrixEntry,
) -> tuple[dict[str, str], _ConanProfile]:
    homebrew_prefix = _required_environment("HOMEBREW_PREFIX")
    flags = ["-Wall", "-Wextra", "-Werror"]
    cache_variables: dict[str, str] = {
        "CMAKE_BUILD_TYPE": "Release" if entry.build_type == "release" else "Debug",
    }

    match entry.compiler, entry.cxx_lib, entry.build_type:
        case "gcc", "libstdc++", "debug":
            return _native_gcc_configuration(
                cache_variables, homebrew_prefix, flags, glibcxx_debug=True
            )
        case "gcc", "libstdc++", "release":
            return _native_gcc_configuration(
                cache_variables, homebrew_prefix, flags, glibcxx_debug=False
            )
        case "clang", "libc++", "hardened":
            return _hardened_libcxx_configuration(
                cache_variables, homebrew_prefix, flags
            )
        case "clang", "libc++", "sanitizers":
            return _clang_libcxx_configuration(
                cache_variables,
                homebrew_prefix,
                flags,
                entry.os,
                sanitizers=True,
            )
        case "clang", "libc++", "debug" | "release":
            return _clang_libcxx_configuration(
                cache_variables,
                homebrew_prefix,
                flags,
                entry.os,
                sanitizers=False,
            )
        case "clang", "libstdc++", "debug" | "release":
            return _clang_libstdcxx_configuration(
                cache_variables, homebrew_prefix, flags, entry.os
            )
        case _:
            raise AssertionError(
                (entry.os, entry.compiler, entry.cxx_lib, entry.build_type)
            )


def _configuration(entry: _MatrixEntry) -> tuple[dict[str, str], _ConanProfile]:
    cache_variables, profile = _toolchain_configuration(entry)
    # The add-on profile is always written, but pointing Conan at it only makes a
    # difference when it carries something: a matrix entry whose dependencies are
    # built exactly as Conan detects them keeps the auto-detected profile alone.
    if profile:
        cache_variables["CONAN_HOST_PROFILE"] = _profile_path()
    return cache_variables, profile


def _write_environment(path: Path, entry: _MatrixEntry) -> None:
    lines = [
        "# Generated by .github/scripts/generate-cpp-ci-config.py.",
        f"# Matrix: {entry}",
    ]
    if entry.build_type == "sanitizers":
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
    subparsers = parser.add_subparsers(dest="command", required=True)

    config = subparsers.add_parser(
        "config", help="Write the CMake, environment and Conan files for one entry"
    )
    config.add_argument(
        "--os",
        choices=sorted(get_args(_OS.evaluate_value())),  # pyright: ignore [reportCallIssue]
        required=True,
    )
    config.add_argument(
        "--compiler",
        choices=sorted(get_args(_Compiler.evaluate_value())),  # pyright: ignore [reportCallIssue]
        required=True,
    )
    config.add_argument(
        "--cxx-lib",
        choices=sorted(get_args(_CxxLib.evaluate_value())),  # pyright: ignore [reportCallIssue]
        required=True,
    )
    config.add_argument(
        "--build-type",
        choices=sorted(get_args(_BuildType.evaluate_value())),  # pyright: ignore [reportCallIssue]
        required=True,
    )
    config.add_argument("--output-dir", default=_CPP_DIR, type=Path)

    matrix = subparsers.add_parser(
        "matrix", help="Print the workflow build matrix as JSON"
    )
    # Defaulted rather than required: `workflow_dispatch` runs supply no hashes.
    matrix.add_argument("--homebrew-downloads-hash-macos", default="")
    matrix.add_argument("--homebrew-downloads-hash-ubuntu", default="")

    return parser.parse_args()


def _emit_matrix(args: argparse.Namespace) -> None:
    homebrew_hashes: dict[_OS, str] = {
        "macos": args.homebrew_downloads_hash_macos,
        "ubuntu": args.homebrew_downloads_hash_ubuntu,
    }
    include = [_github_include(entry, homebrew_hashes) for entry in _matrix()]

    # Ensure that each matrix entry has a unique runId.
    run_ids = {entry["runId"] for entry in include}
    if len(run_ids) != len(include):
        msg = "runId values are not unique"
        raise ValueError(msg)

    # Output in one line for easy consumption in GitHub Actions.
    print(json.dumps({"include": include}))


def _write_configuration(args: argparse.Namespace) -> int:
    try:
        matrix = _parse_matrix(args)
        cache_variables, conan_profile = _configuration(matrix)
    except _ConfigurationError as error:
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
    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "CMakeUserPresets.json").write_text(
        json.dumps(preset, indent=2) + "\n", encoding="utf-8"
    )
    _write_environment(output_dir / "ci.env", matrix)
    (output_dir / "conan-profile-ci").write_text(
        _render_conan_profile(conan_profile), encoding="utf-8"
    )
    return 0


def main() -> int:
    args = _parse_args()
    if args.command == "matrix":
        _emit_matrix(args)
        return 0
    return _write_configuration(args)


if __name__ == "__main__":
    sys.exit(main())

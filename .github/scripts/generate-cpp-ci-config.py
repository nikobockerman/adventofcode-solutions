#!/usr/bin/env python3
"""Generate the C++ CI build matrix and the configuration for one matrix entry."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import sys
from pathlib import Path
from typing import Final, NamedTuple

_REPOSITORY_ROOT: Final = Path(__file__).resolve().parents[2]
_CPP_DIR: Final = _REPOSITORY_ROOT / "solvers" / "cpp"

# Six bytes render as twelve hex characters: enough to separate the handful of
# flag sets written below, while leaving compiler.abi_extra readable in the
# workflow log.
_ABI_HASH_BYTES: Final = 6


class _MatrixEntry(NamedTuple):
    """One C++ build scenario: which compiler, standard library and build type."""

    os: str
    compiler: str
    cxx_lib: str
    build_type: str


class _ConanProfile(NamedTuple):
    """The Conan profile add-on layered on the auto-detected profile.

    Every field is what the profile *means*; `_render_profile` decides how it is
    spelled, so all matrix entries produce the same shape of file.
    """

    # Joined with "-" into compiler.abi_extra, which participates in package_id.
    abi_extra_parts: tuple[str, ...] = ()
    cxxflags: tuple[str, ...] = ()
    # Conan has no combined link-flags conf; the same list feeds exe and shared.
    linkflags: tuple[str, ...] = ()

    def __bool__(self) -> bool:
        # A NamedTuple is a tuple, so an add-on with every field empty is still
        # three elements long and would otherwise be truthy.
        return any((self.abi_extra_parts, self.cxxflags, self.linkflags))


# Runner image hosting each operating system.
_RUNNERS: Final = {"macos": "macos-15", "ubuntu": "ubuntu-24.04"}

# Every scenario CI builds. The workflow obtains its job list from the `matrix`
# subcommand rather than declaring one, so this table is the only place the set of
# scenarios is written down and the two cannot drift apart.
_MATRIX: Final = (
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


class ConfigurationError(ValueError):
    """Raised when a matrix entry cannot be represented by the CI configuration."""


class MissingEnvironmentError(ConfigurationError):
    """Raised when a generated configuration needs an unavailable environment value."""

    def __init__(self, name: str) -> None:
        super().__init__(f"Required environment variable is not set: {name}")


class UnsupportedMatrixError(ConfigurationError):
    """Raised when the workflow matrix specifies an unsupported build."""

    def __init__(self, matrix: _MatrixEntry) -> None:
        super().__init__(f"Unsupported C++ CI matrix entry: {', '.join(matrix)}")


def _required_environment(name: str) -> str:
    value = os.environ.get(name)
    if value:
        return value
    raise MissingEnvironmentError(name)


def _validate_matrix(args: argparse.Namespace) -> None:
    matrix = _MatrixEntry(args.os, args.compiler, args.cxx_lib, args.build_type)
    if matrix not in _MATRIX:
        raise UnsupportedMatrixError(matrix)


def _github_include(
    entry: _MatrixEntry, homebrew_hashes: dict[str, str]
) -> dict[str, str]:
    # Key names are read by the workflow's job name, `if:` conditions and step
    # environments, so they follow GitHub's casing rather than Python's.
    #
    # `runId` identifies one matrix job among all of them, for uses such as
    # per-scenario cache keys. Joining every field carries a new axis into it
    # automatically; `_emit_matrix` checks that the results stay distinct, since
    # joining can alias if an axis value ever contains the separator.
    return {
        "os": entry.os,
        "compiler": entry.compiler,
        "cxxLib": entry.cxx_lib,
        "buildType": entry.build_type,
        "runId": "-".join(entry),
        "runsOn": _RUNNERS[entry.os],
        "homebrew-downloads-hash-from-prepare": homebrew_hashes[entry.os],
    }


def _profile_path() -> str:
    # sourceDir is resolved by CMake, not from the process environment.
    return "auto-cmake;${sourceDir}/conan-profile-ci"


def _conf_lines(profile: _ConanProfile) -> list[str]:
    # Conan reads a conf value back as a Python literal, so json.dumps is both a
    # correct spelling and one that quotes and escapes every flag the same way.
    lines: list[str] = []
    if profile.cxxflags:
        lines.append(f"tools.build:cxxflags={json.dumps(profile.cxxflags)}")
    if profile.linkflags:
        flags = json.dumps(profile.linkflags)
        lines.append(f"tools.build:exelinkflags={flags}")
        lines.append(f"tools.build:sharedlinkflags={flags}")
    return lines


def _conf_hash(conf: list[str]) -> str:
    # BLAKE2 takes the output length as an algorithm parameter, so a short digest
    # is the hash itself rather than a truncation applied afterwards.
    return hashlib.blake2b(
        "\n".join(conf).encode(), digest_size=_ABI_HASH_BYTES
    ).hexdigest()


def _render_profile(profile: _ConanProfile) -> str:
    conf = _conf_lines(profile)
    abi_extra_parts = list(profile.abi_extra_parts)
    if conf:
        # The digest names a set of flags, so it exists only when there are some.
        abi_extra_parts.append(_conf_hash(conf))

    sections: list[list[str]] = []
    if abi_extra_parts:
        sections.append(
            ["[settings]", f"compiler.abi_extra={'-'.join(abi_extra_parts)}"]
        )
    if conf:
        sections.append(["[conf]", *conf])
    if not sections:
        return "# This matrix entry needs no add-on to the auto-detected profile.\n"
    return "\n\n".join("\n".join(section) for section in sections) + "\n"


def _add_clang_compilers(cache_variables: dict[str, str], llvm_prefix: str) -> None:
    cache_variables.update(
        {
            "CMAKE_C_COMPILER": f"{llvm_prefix}/bin/clang",
            "CMAKE_CXX_COMPILER": f"{llvm_prefix}/bin/clang++",
        }
    )


def _native_gcc_configuration(
    cache_variables: dict[str, str], homebrew_prefix: str, flags: list[str]
) -> tuple[dict[str, str], _ConanProfile]:
    gcc_major_version = _required_environment("GCC_MAJOR_VERSION")
    gcc_prefix = f"{homebrew_prefix}/opt/gcc@{gcc_major_version}"
    cache_variables.update(
        {
            "CMAKE_C_COMPILER": f"{gcc_prefix}/bin/gcc-{gcc_major_version}",
            "CMAKE_CXX_COMPILER": f"{gcc_prefix}/bin/g++-{gcc_major_version}",
            "CMAKE_CXX_FLAGS": " ".join(flags),
        }
    )
    # Native GCC builds dependencies exactly as Conan detects them.
    return cache_variables, _ConanProfile()


def _hardened_libcxx_configuration(
    cache_variables: dict[str, str], homebrew_prefix: str, flags: list[str]
) -> tuple[dict[str, str], _ConanProfile]:
    llvm_major_version = _required_environment("LLVM_MAJOR_VERSION")
    llvm_prefix = f"{homebrew_prefix}/opt/llvm@{llvm_major_version}"
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
    profile = _ConanProfile(
        abi_extra_parts=("libc++", "hardened"),
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
    # sanitizers, so the flag hash cannot separate them from a plain libc++
    # build. They still must not share binaries, because the ASan runtime those
    # are linked against belongs to this exact LLVM — hence the explicit tag.
    abi_extra_parts = ("libc++",)
    if sanitizers:
        llvm_full_version = _required_environment("LLVM_FULL_VERSION")
        abi_extra_parts = (*abi_extra_parts, f"sanitizers-{llvm_full_version}")

    profile = _ConanProfile(
        abi_extra_parts=abi_extra_parts,
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
        abi_extra_parts=(f"libstdc++-gcc-{gcc_major_version}",),
        cxxflags=libstdcxx_flags,
        linkflags=conan_linker_flags,
    )
    return cache_variables, profile


def _toolchain_configuration(
    args: argparse.Namespace,
) -> tuple[dict[str, str], _ConanProfile]:
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


def _configuration(args: argparse.Namespace) -> tuple[dict[str, str], _ConanProfile]:
    cache_variables, profile = _toolchain_configuration(args)
    # The add-on profile is always written, but pointing Conan at it only makes a
    # difference when it carries something: a matrix entry whose dependencies are
    # built exactly as Conan detects them keeps the auto-detected profile alone.
    if profile:
        cache_variables["CONAN_HOST_PROFILE"] = _profile_path()
    return cache_variables, profile


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
    subparsers = parser.add_subparsers(dest="command", required=True)

    config = subparsers.add_parser(
        "config", help="Write the CMake, environment and Conan files for one entry"
    )
    config.add_argument(
        "--os", choices=sorted({entry.os for entry in _MATRIX}), required=True
    )
    config.add_argument(
        "--compiler",
        choices=sorted({entry.compiler for entry in _MATRIX}),
        required=True,
    )
    config.add_argument(
        "--cxx-lib",
        choices=sorted({entry.cxx_lib for entry in _MATRIX}),
        required=True,
    )
    config.add_argument(
        "--build-type",
        choices=sorted({entry.build_type for entry in _MATRIX}),
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
    homebrew_hashes = {
        "macos": args.homebrew_downloads_hash_macos,
        "ubuntu": args.homebrew_downloads_hash_ubuntu,
    }
    include = [_github_include(entry, homebrew_hashes) for entry in _MATRIX]
    # Two jobs sharing a runId would quietly share one Conan cache bucket, each
    # restoring the other's packages and rebuilding anyway. Nothing downstream
    # would fail, so catch it here.
    run_ids = {entry["runId"] for entry in include}
    assert len(run_ids) == len(include), "runId values are not unique"
    # One line, so the caller can assign it to a `$GITHUB_OUTPUT` variable.
    print(json.dumps({"include": include}))


def _write_configuration(args: argparse.Namespace) -> int:
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
    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "CMakeUserPresets.json").write_text(
        json.dumps(preset, indent=2) + "\n", encoding="utf-8"
    )
    _write_environment(output_dir / "ci.env", args)
    (output_dir / "conan-profile-ci").write_text(
        _render_profile(conan_profile), encoding="utf-8"
    )
    return 0


def main() -> int:
    args = _parse_args()
    if args.command == "matrix":
        _emit_matrix(args)
        return 0
    return _write_configuration(args)


if __name__ == "__main__":
    raise SystemExit(main())

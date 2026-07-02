#!/usr/bin/env python3
# [MISE] description="Verify binaries load the intended libstdc++/libc++ at runtime"
# [USAGE] arg "<build_dir>" help="CMake build directory to scan"
# [USAGE] arg "<stdlib>" help="Intended C++ standard library" {
# [USAGE]   choices "libstdc++" "libc++"
# [USAGE] }
# [USAGE] arg "<expected_prefix>" help="Prefix the runtime libraries must load from"
#
# Why this exists: -stdlib=... / -L... only affect the *static* link. At runtime the
# loader resolves the bare SONAME (e.g. libstdc++.so.6) via its own search, which can
# silently land on a *system* library that happens to be ABI-compatible. Running the
# tests does not catch that. This task inspects the actual loader resolution of every
# built binary and asserts the intended library loads from <expected_prefix>.
import logging
import os
import platform
import shlex
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

_logger = logging.getLogger(os.environ.get("MISE_TASK_NAME", __name__))

# Sentinel: the binary depends on the SONAME but the loader cannot resolve it.
_NOT_FOUND = "<not-found>"

# Runtime libraries whose load path is pinned, per (stdlib, platform). For libc++ we
# also pin libunwind (LLVM's unwinder, linked via -lunwind).
_SONAMES: dict[tuple[str, str], list[str]] = {
    ("libstdc++", "Linux"): ["libstdc++.so.6"],
    ("libstdc++", "Darwin"): ["libstdc++.6.dylib"],
    ("libc++", "Linux"): ["libc++.so.1", "libunwind.so.1"],
    ("libc++", "Darwin"): ["libc++.1.dylib", "libunwind.1.dylib"],
}

# MIME types (per `file --mime-type`) of the artifacts we inspect: ELF executables
# (position-independent or not), shared libraries, and Mach-O images. Objects,
# archives and text files report other types and are skipped.
_BINARY_MIME_TYPES = frozenset(
    {
        "application/x-executable",
        "application/x-pie-executable",
        "application/x-sharedlib",
        "application/x-mach-binary",
    }
)


def _run(args: list[str]) -> str:
    result = subprocess.run(  # noqa: S603
        args,
        check=False,
        text=True,
        stdin=subprocess.DEVNULL,
        capture_output=True,
    )
    if result.returncode != 0:
        # Surface unexpected tool failures instead of silently skipping the binary.
        _logger.warning(
            "%s exited %d: %s",
            shlex.join(args),
            result.returncode,
            result.stderr.strip(),
        )
    return result.stdout


def _is_binary(path: Path) -> bool:
    mime = _run(["file", "--brief", "--mime-type", str(path)]).strip()
    return mime in _BINARY_MIME_TYPES


def _iter_binaries(build_dir: Path) -> Iterator[Path]:
    for path in sorted(build_dir.rglob("*")):
        if "CMakeFiles" in path.parts or not path.is_file():
            continue
        if _is_binary(path):
            yield path


def _resolved_libs_linux(binary: Path) -> dict[str, str]:
    # One ldd call yields "SONAME => /resolved/path" (or "=> not found") per dependency.
    libs: dict[str, str] = {}
    for line in _run(["ldd", str(binary)]).splitlines():
        fields = line.split()
        if "=>" not in fields:
            continue
        target = fields[fields.index("=>") + 1]
        libs[fields[0]] = _NOT_FOUND if target == "not" else target
    return libs


def _expand_at_path(raw: str, loader: str, *, is_dylib: bool) -> str:
    # @loader_path -> the inspected file's own dir (valid for exe and dylib).
    # @executable_path -> the main executable's dir, which equals the inspected file's
    # dir only when this file is the executable; for a dylib it can't resolve here.
    raw = raw.replace("@loader_path", loader)
    if not is_dylib:
        raw = raw.replace("@executable_path", loader)
    return raw


def _macos_rpaths(
    load_lines: list[str], loader: str, *, is_dylib: bool
) -> Iterator[str]:
    for index, line in enumerate(load_lines):
        if line.strip() != "cmd LC_RPATH":
            continue
        for follow in load_lines[index + 1 : index + 4]:
            stripped = follow.strip()
            if stripped.startswith("path "):
                path = stripped.split(" ", 2)[1]
                yield _expand_at_path(path, loader, is_dylib=is_dylib)
                break


def _resolve_install_name(
    binary: Path, name: str, rpaths: list[str], *, is_dylib: bool
) -> str:
    if name.startswith("/"):
        # Absolute install name: dyld uses it verbatim. A missing file is unresolved,
        # consistent with the @rpath / @loader_path branches (and avoids a false pass
        # when expected_prefix is broad).
        return name if Path(name).exists() else _NOT_FOUND
    if name.startswith("@rpath/"):
        suffix = name[len("@rpath/") :]
        for rpath in rpaths:
            candidate = Path(rpath) / suffix
            if candidate.exists():
                return str(candidate)
        return _NOT_FOUND
    expanded = _expand_at_path(name, str(binary.parent), is_dylib=is_dylib)
    if expanded.startswith("/"):  # @loader_path, or @executable_path for an executable
        return expanded if Path(expanded).exists() else _NOT_FOUND
    return _NOT_FOUND  # e.g. @executable_path in a dylib: not statically resolvable


def _resolved_libs_macos(binary: Path) -> dict[str, str]:
    # otool -l gives LC_ID_DYLIB (exe vs dylib) and LC_RPATH; otool -L the dependencies.
    load_lines = _run(["otool", "-l", str(binary)]).splitlines()
    is_dylib = any(line.strip() == "cmd LC_ID_DYLIB" for line in load_lines)
    loader = str(binary.parent)
    dep_lines = _run(["otool", "-L", str(binary)]).splitlines()[1:]
    names = [n for n in (line.strip().split(" ", 1)[0] for line in dep_lines) if n]
    rpaths: list[str] = []
    if any(n.startswith("@rpath/") for n in names):
        rpaths = list(_macos_rpaths(load_lines, loader, is_dylib=is_dylib))
    libs: dict[str, str] = {}
    for name in names:
        libs[name.rsplit("/", 1)[-1]] = _resolve_install_name(
            binary, name, rpaths, is_dylib=is_dylib
        )
    return libs


def _resolved_libs(binary: Path) -> dict[str, str]:
    if platform.system() == "Darwin":
        return _resolved_libs_macos(binary)
    return _resolved_libs_linux(binary)


def _under_prefix(path: str, prefix: str) -> bool:
    # Resolve both sides so a Homebrew opt/... prefix matches its Cellar real path.
    real_path = Path(path).resolve()
    real_prefix = Path(prefix).resolve()
    return real_path == real_prefix or real_prefix in real_path.parents


def _check(
    name: str, libs: dict[str, str], soname: str, expected_prefix: str
) -> bool | None:
    # None: the binary does not depend on `soname`. True/False: pass/fail (logged).
    path = libs.get(soname)
    if path is None:
        return None
    if path == _NOT_FOUND:
        _logger.error("FAIL  %s: %s not found at runtime", name, soname)
        return False
    if _under_prefix(path, expected_prefix):
        _logger.info("ok    %s: %s => %s", name, soname, path)
        return True
    msg = "FAIL  %s: %s => %s (want under %s)"
    _logger.error(msg, name, soname, path, expected_prefix)
    return False


def _verify(binaries: list[Path], sonames: list[str], expected_prefix: str) -> bool:
    ok = True
    seen: set[str] = set()
    for binary in binaries:
        libs = _resolved_libs(binary)
        for soname in sonames:
            result = _check(binary.name, libs, soname, expected_prefix)
            if result is None:
                continue
            seen.add(soname)
            ok = ok and result
    # Guard against silently verifying nothing (wrong build dir or unexpected linkage).
    for soname in sonames:
        if soname not in seen:
            _logger.error("FAIL  no binary depends on %s; nothing verified", soname)
            ok = False
    return ok


def main() -> bool:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    build_dir = Path(os.environ["usage_build_dir"])  # noqa: SIM112
    stdlib = os.environ["usage_stdlib"]  # noqa: SIM112
    expected_prefix = os.environ["usage_expected_prefix"].rstrip("/")  # noqa: SIM112

    sonames = _SONAMES.get((stdlib, platform.system()))
    if sonames is None:
        _logger.error("Unsupported: stdlib=%s platform=%s", stdlib, platform.system())
        return False
    binaries = list(_iter_binaries(build_dir))
    if not binaries:
        _logger.error("No binaries found under %s", build_dir)
        return False

    if not _verify(binaries, sonames, expected_prefix):
        return False
    _logger.info("runtime-stdlib OK: %s loads from %s", stdlib, expected_prefix)
    return True


if __name__ == "__main__":
    if not main():
        sys.exit(1)

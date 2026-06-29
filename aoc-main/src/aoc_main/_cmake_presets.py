"""Minimal reader for CMake preset files.

CMake's preset schema (``CMakePresets.json`` / ``CMakeUserPresets.json``) is
large; this module implements only the slice the C++ solver build needs:

* looking up a preset by *type* and *name*, with user presets taking precedence
  over project presets (mirroring CMake's own override order);
* following ``include`` directives so a preset can live in a file pulled in by
  the entry-point file, including recursively;
* expanding a minimal set of preset macros in those include paths
  (see :func:`_expand_include`);
* finding the configure step of a workflow preset;
* resolving the ``binaryDir`` of a configure preset, walking ``inherits`` chains
  when the field is not set on the preset directly.

Macros outside that minimal set (e.g. ``${sourceDir}``) and other schema
features are intentionally unsupported; an include path that uses one raises
rather than silently producing a wrong path.
"""

import json
import os
import pathlib
import platform
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from aoc_main import _logging

if TYPE_CHECKING:
    from collections.abc import Iterator

_logger = _logging.logger

PresetType = Literal["build", "configure", "workflow"]


class CMakePresetError(Exception):
    """Raised when the preset files cannot satisfy a requested lookup."""


def _host_system_name() -> str:
    """Value CMake exposes as ``${hostSystemName}`` / ``CMAKE_HOST_SYSTEM_NAME``.

    ``platform.system()`` returns ``Darwin`` / ``Linux`` / ``Windows``, which is
    exactly the spelling CMake uses for the host OS name. Kept as a module-level
    function so tests can substitute a value without faking the whole platform.
    """
    return platform.system()


# Matches the two macro forms this module expands: ``${macro}`` and
# ``$penv{var}`` / ``$env{var}``. ``$penv`` reads the *parent* (process)
# environment; ``$env`` reads preset-defined environment and is unsupported in
# include paths.
_INCLUDE_MACRO_RE = re.compile(
    r"\$(?:(?P<scope>p?env)\{(?P<var>[^}]+)\}|\{(?P<macro>[^}]+)\})"
)


def _expand_include(value: str) -> str:
    """Expand the supported preset macros in an ``include`` entry.

    The supported set is deliberately small: ``${hostSystemName}`` and
    ``$penv{NAME}`` (a parent-environment lookup). Any other macro raises
    :class:`CMakePresetError` so an unsupported construct fails loudly instead of
    resolving to a nonsensical path.
    """

    def replace(match: re.Match[str]) -> str:
        scope = match.group("scope")
        if scope == "penv":
            var = match.group("var")
            try:
                return os.environ[var]
            except KeyError:
                msg = (
                    f"Environment variable not set for include macro: {match.group(0)}"
                )
                raise CMakePresetError(msg) from None

        if scope is None and match.group("macro") == "hostSystemName":
            return _host_system_name()

        msg = f"Unsupported macro in include path: {match.group(0)}"
        raise CMakePresetError(msg)

    return _INCLUDE_MACRO_RE.sub(replace, value)


@dataclass(frozen=True)
class _PresetFile:
    """One parsed preset file: its absolute path plus the decoded JSON."""

    path: pathlib.Path
    config: dict[str, Any]

    @property
    def includes(self) -> list[pathlib.Path]:
        """Absolute paths this file's ``include`` list points at.

        Relative entries resolve against this file's directory (CMake's rule),
        and macros are expanded along the way.
        """
        base = self.path.parent
        resolved: list[pathlib.Path] = []
        for raw in self.config.get("include", []):
            include_path = pathlib.Path(_expand_include(raw))
            if not include_path.is_absolute():
                include_path = base / include_path
            resolved.append(include_path)
        return resolved

    def presets(self, preset_type: PresetType) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = self.config.get(f"{preset_type}Presets", [])
        return result


class CMakePresets:
    """Reads CMake preset files from a directory and answers queries about them.

    Pass the directory that contains ``CMakePresets.json`` (and optionally
    ``CMakeUserPresets.json``). Files are read lazily and cached on first
    access, so an instance reflects their contents at that point. A missing
    file is treated as containing no presets.

    Lookups follow ``include`` directives: the user file implicitly includes the
    project file (as CMake does), and any file may pull in further files, which
    are searched recursively.
    """

    def __init__(self, root_dir: pathlib.Path) -> None:
        self._root_dir = root_dir
        self._file_cache: dict[pathlib.Path, _PresetFile | None] = {}

    def _load_file(self, path: pathlib.Path) -> _PresetFile | None:
        """Load and cache a preset file; ``None`` if it does not exist."""
        path = path.absolute()
        if path not in self._file_cache:
            if path.exists():
                self._file_cache[path] = _PresetFile(path, json.loads(path.read_text()))
            else:
                self._file_cache[path] = None
        return self._file_cache[path]

    def _walk(
        self,
        path: pathlib.Path,
        *,
        visited: set[pathlib.Path],
        implicit: tuple[pathlib.Path, ...] = (),
    ) -> Iterator[_PresetFile]:
        """Yield ``path`` and every file it includes, depth-first.

        ``visited`` guards against re-yielding a file reached through more than
        one include path (a diamond) and against cycles. ``implicit`` lists
        files included by CMake convention rather than by an ``include`` entry
        (the project file, included by the user file); those may be absent,
        whereas an explicit include that is missing is an error.
        """
        path = path.absolute()
        if path in visited:
            return
        visited.add(path)

        preset_file = self._load_file(path)
        if preset_file is None:
            return
        yield preset_file

        for include_path in implicit:
            yield from self._walk(include_path, visited=visited)

        for include_path in preset_file.includes:
            if self._load_file(include_path) is None:
                msg = f"Included preset file does not exist: {include_path}"
                raise CMakePresetError(msg)
            yield from self._walk(include_path, visited=visited)

    def _iter_preset_files(self) -> Iterator[_PresetFile]:
        """Yield every reachable preset file, user presets first.

        CMake has ``CMakeUserPresets.json`` implicitly include
        ``CMakePresets.json``; that is modelled here as an implicit include so a
        preset defined only in the project file is still found when looking up
        from the user file.
        """
        visited: set[pathlib.Path] = set()
        project = (self._root_dir / "CMakePresets.json").absolute()
        user = (self._root_dir / "CMakeUserPresets.json").absolute()
        yield from self._walk(user, visited=visited, implicit=(project,))
        yield from self._walk(project, visited=visited)

    def _get_preset(self, preset_type: PresetType, name: str) -> dict[str, Any] | None:
        for preset_file in self._iter_preset_files():
            for preset in preset_file.presets(preset_type):
                if preset["name"] == name:
                    return preset
        return None

    def workflow_configure_preset_name(self, workflow_name: str) -> str:
        """Return the configure step's preset name for a workflow preset."""
        workflow_preset = self._get_preset("workflow", workflow_name)
        if workflow_preset is None:
            msg = f"Requested workflow preset not found: {workflow_name}"
            raise CMakePresetError(msg)

        try:
            return next(
                step["name"]
                for step in workflow_preset["steps"]
                if step["type"] == "configure"
            )
        except KeyError as e:
            msg = f"Invalid CMake Preset json for workflow preset: {workflow_name}"
            raise CMakePresetError(msg) from e
        except StopIteration:
            msg = f"No configure step found for workflow: {workflow_name}"
            raise CMakePresetError(msg) from None

    def binary_dir(self, configure_preset_name: str) -> pathlib.Path:
        """Resolve the ``binaryDir`` of a configure preset.

        If the named preset does not set ``binaryDir`` itself, its ``inherits``
        parents are searched breadth-first and the first one that sets the field
        wins.
        """
        pending = [configure_preset_name]
        while pending:
            name = pending.pop(0)
            preset = self._get_preset("configure", name)
            if preset is None:
                msg = f"Configure preset not found: {name}"
                raise CMakePresetError(msg)

            binary_dir = preset.get("binaryDir")
            if binary_dir is not None:
                _logger.debug("Found binaryDir from preset %s: %s", name, binary_dir)
                return pathlib.Path(binary_dir)

            _logger.debug(
                "binaryDir not set on preset %s; checking inherited presets", name
            )
            pending.extend(preset.get("inherits", []))

        msg = f"binaryDir not found for configure preset {configure_preset_name}"
        raise CMakePresetError(msg)

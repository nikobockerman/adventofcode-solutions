"""Minimal reader for CMake preset files.

CMake's preset schema (``CMakePresets.json`` / ``CMakeUserPresets.json``) is
large; this module implements only the slice the C++ solver build needs:

* looking up a preset by *type* and *name*, with user presets taking precedence
  over project presets (mirroring CMake's own override order);
* finding the configure step of a workflow preset;
* resolving the ``binaryDir`` of a configure preset, walking ``inherits`` chains
  when the field is not set on the preset directly.

Features such as ``include`` and macro expansion (e.g. ``${sourceDir}``) are
intentionally unsupported.
"""

import json
import pathlib
from functools import cached_property
from typing import Any, Literal

from aoc_main import _logging

_logger = _logging.logger

PresetType = Literal["build", "configure", "workflow"]


class CMakePresetError(Exception):
    """Raised when the preset files cannot satisfy a requested lookup."""


class CMakePresets:
    """Reads CMake preset files from a directory and answers queries about them.

    Pass the directory that contains ``CMakePresets.json`` (and optionally
    ``CMakeUserPresets.json``). Files are read lazily and cached on first
    access, so an instance reflects their contents at that point. A missing
    file is treated as containing no presets.
    """

    def __init__(self, root_dir: pathlib.Path) -> None:
        self._root_dir = root_dir

    @cached_property
    def _user_presets(self) -> dict[str, Any]:
        return self._load(self._root_dir / "CMakeUserPresets.json")

    @cached_property
    def _project_presets(self) -> dict[str, Any]:
        return self._load(self._root_dir / "CMakePresets.json")

    @staticmethod
    def _load(preset_file: pathlib.Path) -> dict[str, Any]:
        if not preset_file.exists():
            return {}
        return json.loads(preset_file.read_text())

    def _get_preset(self, preset_type: PresetType, name: str) -> dict[str, Any] | None:
        for presets in (self._user_presets, self._project_presets):
            preset = next(
                (
                    preset
                    for preset in presets.get(f"{preset_type}Presets", [])
                    if preset["name"] == name
                ),
                None,
            )
            if preset is not None:
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

import json
import pathlib

import pytest

from aoc_main._cmake_presets import CMakePresetError, CMakePresets


def _write_presets(
    root: pathlib.Path,
    presets: dict[str, object],
    *,
    user: bool = False,
) -> None:
    name = "CMakeUserPresets.json" if user else "CMakePresets.json"
    (root / name).write_text(json.dumps(presets))


def test_binary_dir_set_on_preset(tmp_path: pathlib.Path) -> None:
    _write_presets(
        tmp_path,
        {"configurePresets": [{"name": "aoc", "binaryDir": "build/aoc"}]},
    )
    assert CMakePresets(tmp_path).binary_dir("aoc") == pathlib.Path("build/aoc")


def test_binary_dir_inherited_from_parent(tmp_path: pathlib.Path) -> None:
    _write_presets(
        tmp_path,
        {
            "configurePresets": [
                {"name": "aoc", "inherits": ["base"]},
                {"name": "base", "binaryDir": "build/base"},
            ]
        },
    )
    assert CMakePresets(tmp_path).binary_dir("aoc") == pathlib.Path("build/base")


def test_binary_dir_on_preset_wins_over_inherited(tmp_path: pathlib.Path) -> None:
    _write_presets(
        tmp_path,
        {
            "configurePresets": [
                {"name": "aoc", "binaryDir": "build/aoc", "inherits": ["base"]},
                {"name": "base", "binaryDir": "build/base"},
            ]
        },
    )
    assert CMakePresets(tmp_path).binary_dir("aoc") == pathlib.Path("build/aoc")


def test_binary_dir_inheritance_is_breadth_first(tmp_path: pathlib.Path) -> None:
    # `aoc` inherits two parents; the first listed parent's value is preferred
    # over a value reachable only through the second parent's own grandparent.
    _write_presets(
        tmp_path,
        {
            "configurePresets": [
                {"name": "aoc", "inherits": ["first", "second"]},
                {"name": "first", "binaryDir": "build/first"},
                {"name": "second", "inherits": ["grandparent"]},
                {"name": "grandparent", "binaryDir": "build/grandparent"},
            ]
        },
    )
    assert CMakePresets(tmp_path).binary_dir("aoc") == pathlib.Path("build/first")


def test_presets_are_read_from_both_files(tmp_path: pathlib.Path) -> None:
    # CMake requires preset names to be unique across the union of the project
    # and user files, so both files are consulted but never collide by name.
    _write_presets(
        tmp_path,
        {"configurePresets": [{"name": "project", "binaryDir": "build/project"}]},
    )
    _write_presets(
        tmp_path,
        {"configurePresets": [{"name": "user", "binaryDir": "build/user"}]},
        user=True,
    )
    presets = CMakePresets(tmp_path)
    assert presets.binary_dir("project") == pathlib.Path("build/project")
    assert presets.binary_dir("user") == pathlib.Path("build/user")


def test_user_preset_can_inherit_from_project_preset(tmp_path: pathlib.Path) -> None:
    _write_presets(
        tmp_path,
        {"configurePresets": [{"name": "base", "binaryDir": "build/base"}]},
    )
    _write_presets(
        tmp_path,
        {"configurePresets": [{"name": "aoc", "inherits": ["base"]}]},
        user=True,
    )
    assert CMakePresets(tmp_path).binary_dir("aoc") == pathlib.Path("build/base")


def test_binary_dir_unknown_preset_raises(tmp_path: pathlib.Path) -> None:
    _write_presets(tmp_path, {"configurePresets": []})
    with pytest.raises(CMakePresetError, match="Configure preset not found: missing"):
        CMakePresets(tmp_path).binary_dir("missing")


def test_binary_dir_missing_through_inheritance_raises(
    tmp_path: pathlib.Path,
) -> None:
    _write_presets(
        tmp_path,
        {
            "configurePresets": [
                {"name": "aoc", "inherits": ["base"]},
                {"name": "base"},
            ]
        },
    )
    with pytest.raises(CMakePresetError, match="binaryDir not found"):
        CMakePresets(tmp_path).binary_dir("aoc")


def test_missing_preset_files_are_treated_as_empty(tmp_path: pathlib.Path) -> None:
    with pytest.raises(CMakePresetError, match="Configure preset not found: aoc"):
        CMakePresets(tmp_path).binary_dir("aoc")


def test_workflow_configure_preset_name(tmp_path: pathlib.Path) -> None:
    _write_presets(
        tmp_path,
        {
            "workflowPresets": [
                {
                    "name": "ci",
                    "steps": [
                        {"type": "configure", "name": "aoc"},
                        {"type": "build", "name": "aoc"},
                    ],
                }
            ]
        },
    )
    assert CMakePresets(tmp_path).workflow_configure_preset_name("ci") == "aoc"


def test_workflow_lookup_uses_user_presets(tmp_path: pathlib.Path) -> None:
    _write_presets(
        tmp_path,
        {
            "workflowPresets": [
                {"name": "ci", "steps": [{"type": "configure", "name": "user-aoc"}]}
            ]
        },
        user=True,
    )
    assert CMakePresets(tmp_path).workflow_configure_preset_name("ci") == "user-aoc"


def test_workflow_unknown_raises(tmp_path: pathlib.Path) -> None:
    _write_presets(tmp_path, {"workflowPresets": []})
    with pytest.raises(
        CMakePresetError, match="Requested workflow preset not found: ci"
    ):
        CMakePresets(tmp_path).workflow_configure_preset_name("ci")


def test_workflow_without_configure_step_raises(tmp_path: pathlib.Path) -> None:
    _write_presets(
        tmp_path,
        {
            "workflowPresets": [
                {"name": "ci", "steps": [{"type": "build", "name": "aoc"}]}
            ]
        },
    )
    with pytest.raises(CMakePresetError, match="No configure step found for workflow"):
        CMakePresets(tmp_path).workflow_configure_preset_name("ci")


def test_workflow_with_malformed_steps_raises(tmp_path: pathlib.Path) -> None:
    _write_presets(
        tmp_path,
        {"workflowPresets": [{"name": "ci", "steps": [{"type": "configure"}]}]},
    )
    with pytest.raises(CMakePresetError, match="Invalid CMake Preset json"):
        CMakePresets(tmp_path).workflow_configure_preset_name("ci")

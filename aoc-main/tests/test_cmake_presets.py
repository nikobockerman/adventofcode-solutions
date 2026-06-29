import json
import pathlib

import pytest

from aoc_main._cmake_presets import CMakePresetError, CMakePresets

# The two filenames CMake recognises by convention; other names are only reached
# through an `include`. Spelling them as constants keeps call-sites readable and
# lets include lists refer to the same value.
_PROJECT_PRESETS = "CMakePresets.json"
_USER_PRESETS = "CMakeUserPresets.json"


def _write_presets(root: pathlib.Path, name: str, presets: dict[str, object]) -> None:
    (root / name).write_text(json.dumps(presets))


def test_binary_dir_set_on_preset(tmp_path: pathlib.Path) -> None:
    _write_presets(
        tmp_path,
        _PROJECT_PRESETS,
        {"configurePresets": [{"name": "aoc", "binaryDir": "build/aoc"}]},
    )
    assert CMakePresets(tmp_path).binary_dir("aoc") == pathlib.Path("build/aoc")


def test_binary_dir_inherited_from_parent(tmp_path: pathlib.Path) -> None:
    _write_presets(
        tmp_path,
        _PROJECT_PRESETS,
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
        _PROJECT_PRESETS,
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
        _PROJECT_PRESETS,
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
        _PROJECT_PRESETS,
        {"configurePresets": [{"name": "project", "binaryDir": "build/project"}]},
    )
    _write_presets(
        tmp_path,
        _USER_PRESETS,
        {"configurePresets": [{"name": "user", "binaryDir": "build/user"}]},
    )
    presets = CMakePresets(tmp_path)
    assert presets.binary_dir("project") == pathlib.Path("build/project")
    assert presets.binary_dir("user") == pathlib.Path("build/user")


def test_user_preset_can_inherit_from_project_preset(tmp_path: pathlib.Path) -> None:
    _write_presets(
        tmp_path,
        _PROJECT_PRESETS,
        {"configurePresets": [{"name": "base", "binaryDir": "build/base"}]},
    )
    _write_presets(
        tmp_path,
        _USER_PRESETS,
        {"configurePresets": [{"name": "aoc", "inherits": ["base"]}]},
    )
    assert CMakePresets(tmp_path).binary_dir("aoc") == pathlib.Path("build/base")


def test_binary_dir_unknown_preset_raises(tmp_path: pathlib.Path) -> None:
    _write_presets(tmp_path, _PROJECT_PRESETS, {"configurePresets": []})
    with pytest.raises(CMakePresetError, match="Configure preset not found: missing"):
        CMakePresets(tmp_path).binary_dir("missing")


def test_binary_dir_missing_through_inheritance_raises(
    tmp_path: pathlib.Path,
) -> None:
    _write_presets(
        tmp_path,
        _PROJECT_PRESETS,
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
        _PROJECT_PRESETS,
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
        _USER_PRESETS,
        {
            "workflowPresets": [
                {"name": "ci", "steps": [{"type": "configure", "name": "user-aoc"}]}
            ]
        },
    )
    assert CMakePresets(tmp_path).workflow_configure_preset_name("ci") == "user-aoc"


def test_workflow_unknown_raises(tmp_path: pathlib.Path) -> None:
    _write_presets(tmp_path, _PROJECT_PRESETS, {"workflowPresets": []})
    with pytest.raises(
        CMakePresetError, match="Requested workflow preset not found: ci"
    ):
        CMakePresets(tmp_path).workflow_configure_preset_name("ci")


def test_workflow_without_configure_step_raises(tmp_path: pathlib.Path) -> None:
    _write_presets(
        tmp_path,
        _PROJECT_PRESETS,
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
        _PROJECT_PRESETS,
        {"workflowPresets": [{"name": "ci", "steps": [{"type": "configure"}]}]},
    )
    with pytest.raises(CMakePresetError, match="Invalid CMake Preset json"):
        CMakePresets(tmp_path).workflow_configure_preset_name("ci")


def test_include_pulls_in_preset_from_another_file(tmp_path: pathlib.Path) -> None:
    _write_presets(tmp_path, _USER_PRESETS, {"include": ["extra.json"]})
    _write_presets(
        tmp_path,
        "extra.json",
        {"configurePresets": [{"name": "aoc", "binaryDir": "build/aoc"}]},
    )
    assert CMakePresets(tmp_path).binary_dir("aoc") == pathlib.Path("build/aoc")


def test_include_is_recursive(tmp_path: pathlib.Path) -> None:
    _write_presets(tmp_path, _USER_PRESETS, {"include": ["mid.json"]})
    _write_presets(tmp_path, "mid.json", {"include": ["leaf.json"]})
    _write_presets(
        tmp_path,
        "leaf.json",
        {"configurePresets": [{"name": "aoc", "binaryDir": "build/aoc"}]},
    )
    assert CMakePresets(tmp_path).binary_dir("aoc") == pathlib.Path("build/aoc")


def test_inherits_resolves_across_included_file(tmp_path: pathlib.Path) -> None:
    # A preset can inherit a parent that lives in an included file.
    _write_presets(
        tmp_path,
        _USER_PRESETS,
        {
            "include": ["base.json"],
            "configurePresets": [{"name": "aoc", "inherits": ["base"]}],
        },
    )
    _write_presets(
        tmp_path,
        "base.json",
        {"configurePresets": [{"name": "base", "binaryDir": "build/base"}]},
    )
    assert CMakePresets(tmp_path).binary_dir("aoc") == pathlib.Path("build/base")


def test_included_paths_resolve_relative_to_including_file(
    tmp_path: pathlib.Path,
) -> None:
    # `mid.json` lives in a subdirectory and its own include must resolve against
    # that subdirectory, not the project root.
    sub = tmp_path / "sub"
    sub.mkdir()
    _write_presets(tmp_path, _USER_PRESETS, {"include": ["sub/mid.json"]})
    _write_presets(sub, "mid.json", {"include": ["leaf.json"]})
    _write_presets(
        sub,
        "leaf.json",
        {"configurePresets": [{"name": "aoc", "binaryDir": "build/aoc"}]},
    )
    assert CMakePresets(tmp_path).binary_dir("aoc") == pathlib.Path("build/aoc")


def test_project_presets_referenced_from_included_file(tmp_path: pathlib.Path) -> None:
    # Only the user file implicitly includes CMakePresets.json; a file deeper in
    # the include graph must include it explicitly to see its presets.
    _write_presets(tmp_path, _USER_PRESETS, {"include": ["base.json"]})
    _write_presets(
        tmp_path,
        "base.json",
        {
            "include": [_PROJECT_PRESETS],
            "configurePresets": [{"name": "aoc", "inherits": ["project-base"]}],
        },
    )
    _write_presets(
        tmp_path,
        _PROJECT_PRESETS,
        {"configurePresets": [{"name": "project-base", "binaryDir": "build/project"}]},
    )
    assert CMakePresets(tmp_path).binary_dir("aoc") == pathlib.Path("build/project")


def test_missing_explicit_include_raises(tmp_path: pathlib.Path) -> None:
    _write_presets(tmp_path, _USER_PRESETS, {"include": ["does-not-exist.json"]})
    with pytest.raises(CMakePresetError, match="Included preset file does not exist"):
        CMakePresets(tmp_path).binary_dir("aoc")


def test_diamond_include_is_resolved_once(tmp_path: pathlib.Path) -> None:
    # `left` and `right` both include `shared`; the shared file must still be
    # traversable (the visited-set must not double-process or fail on it).
    _write_presets(tmp_path, _USER_PRESETS, {"include": ["left.json", "right.json"]})
    _write_presets(tmp_path, "left.json", {"include": ["shared.json"]})
    _write_presets(tmp_path, "right.json", {"include": ["shared.json"]})
    _write_presets(
        tmp_path,
        "shared.json",
        {"configurePresets": [{"name": "aoc", "binaryDir": "build/aoc"}]},
    )
    assert CMakePresets(tmp_path).binary_dir("aoc") == pathlib.Path("build/aoc")


def test_include_expands_host_system_name(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("aoc_main._cmake_presets._host_system_name", lambda: "Linux")
    _write_presets(
        tmp_path,
        _USER_PRESETS,
        {"include": ["CMakeUserPresets-${hostSystemName}.json"]},
    )
    _write_presets(
        tmp_path,
        "CMakeUserPresets-Linux.json",
        {"configurePresets": [{"name": "aoc", "binaryDir": "build/linux"}]},
    )
    assert CMakePresets(tmp_path).binary_dir("aoc") == pathlib.Path("build/linux")


def test_include_expands_penv(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOST_ARCH", "arm64")
    _write_presets(
        tmp_path,
        _USER_PRESETS,
        {"include": ["CMakeUserPresets-$penv{HOST_ARCH}.json"]},
    )
    _write_presets(
        tmp_path,
        "CMakeUserPresets-arm64.json",
        {"configurePresets": [{"name": "aoc", "binaryDir": "build/arm64"}]},
    )
    assert CMakePresets(tmp_path).binary_dir("aoc") == pathlib.Path("build/arm64")


def test_include_unset_penv_raises(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("HOST_ARCH", raising=False)
    _write_presets(
        tmp_path,
        _USER_PRESETS,
        {"include": ["CMakeUserPresets-$penv{HOST_ARCH}.json"]},
    )
    with pytest.raises(CMakePresetError, match="Environment variable not set"):
        CMakePresets(tmp_path).binary_dir("aoc")


def test_include_unsupported_macro_raises(tmp_path: pathlib.Path) -> None:
    _write_presets(
        tmp_path,
        _USER_PRESETS,
        {"include": ["${sourceDir}/extra.json"]},
    )
    with pytest.raises(CMakePresetError, match="Unsupported macro in include path"):
        CMakePresets(tmp_path).binary_dir("aoc")

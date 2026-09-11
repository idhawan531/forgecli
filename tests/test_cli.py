from pathlib import Path

from typer.testing import CliRunner

from forgecli.cli import app
from forgecli.generator import scaffold_project
from forgecli.templates import TEMPLATES

runner = CliRunner()


def test_generate_valid_description_creates_expected_files(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        app,
        ["generate", "a rest api for short links", "-o", str(tmp_path)],
    )
    assert result.exit_code == 0
    generated = tmp_path / "rest-api-short-links"
    assert generated.exists()
    assert (generated / "main.py").exists()
    assert (generated / "README.md").exists()
    assert (generated / "requirements.txt").exists()


def test_generate_empty_description_exits_with_error(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["generate", "   ", "-o", str(tmp_path)])
    assert result.exit_code == 1
    assert "description must not be empty" in result.stdout


def test_generate_invalid_template_exits_with_helpful_message(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        app,
        ["generate", "a thing", "--template", "unknown-template", "-o", str(tmp_path)],
    )
    assert result.exit_code == 1
    assert "invalid template" in result.stdout
    assert "fastapi_api" in result.stdout


def test_generate_name_overrides_derived_folder_name(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        app,
        ["generate", "a rest api for short links", "--name", "My Custom Project", "-o", str(tmp_path)],
    )
    assert result.exit_code == 0
    assert (tmp_path / "my-custom-project").exists()


def test_templates_command_lists_all_templates() -> None:
    result = runner.invoke(app, ["templates"])
    assert result.exit_code == 0
    assert "fastapi_api" in result.stdout
    assert "vite_react" in result.stdout
    assert "rich_tui" in result.stdout


def test_generate_twice_creates_incremented_folder(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    args = ["generate", "a rest api for short links", "-o", str(tmp_path)]
    first = runner.invoke(app, args)
    second = runner.invoke(app, args)
    assert first.exit_code == 0
    assert second.exit_code == 0
    assert (tmp_path / "rest-api-short-links").exists()
    assert (tmp_path / "rest-api-short-links-1").exists()


def test_vite_react_preview_contains_description(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    description = "a react dashboard for tracking habits"
    result = runner.invoke(
        app,
        ["generate", description, "--template", "vite_react", "-o", str(tmp_path)],
    )

    assert result.exit_code == 0
    assert "Preview: src/App.jsx" in result.stdout
    assert description in result.stdout


def test_every_template_preview_file_is_generated(tmp_path: Path) -> None:
    for template in TEMPLATES.values():
        project_path = scaffold_project(
            "a project generated for preview coverage",
            output_dir=str(tmp_path / template.key),
            template=template,
        )
        assert (project_path / template.preview_file).is_file()


def test_version_flag_exits_zero_and_prints_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "forgecli" in result.stdout
    # A version string should contain at least one digit.
    assert any(char.isdigit() for char in result.stdout)


def test_demo_creates_one_project_per_registered_template(tmp_path: Path) -> None:
    result = runner.invoke(app, ["demo", "-o", str(tmp_path)])
    assert result.exit_code == 0

    project_dirs = {entry.name for entry in tmp_path.iterdir() if entry.is_dir()}
    assert len(project_dirs) == len(TEMPLATES)
    for template in TEMPLATES.values():
        expected_dir_name = template.key.replace("_", "-")
        assert expected_dir_name in project_dirs
        assert (tmp_path / expected_dir_name / template.preview_file).is_file()

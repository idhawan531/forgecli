from pathlib import Path

from typer.testing import CliRunner

from forgecli.cli import app

runner = CliRunner()


def test_generate_valid_description_creates_expected_files(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        app,
        ["generate", "a rest api for short links", "-o", str(tmp_path)],
    )
    assert result.exit_code == 0
    generated = tmp_path / "rest-api-for-short"
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
    assert (tmp_path / "rest-api-for-short").exists()
    assert (tmp_path / "rest-api-for-short-1").exists()

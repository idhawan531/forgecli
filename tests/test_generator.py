from pathlib import Path

from forgecli.generator import _slugify, _unique_project_path, scaffold_project
from forgecli.templates import TEMPLATES


def test_slugify_truncates_and_drops_leading_stopwords() -> None:
    description = "A minimal URL shortener API with FastAPI and in-memory storage"
    assert _slugify(description) == "url-shortener-api-with"


def test_slugify_handles_unicode_and_punctuation() -> None:
    assert _slugify("Créate: café tracker!!!") == "cafe-tracker"


def test_slugify_all_stopwords_defaults() -> None:
    assert _slugify("a simple minimal build") == "forgecli-project"


def test_slugify_empty_defaults() -> None:
    assert _slugify("") == "forgecli-project"


def test_unique_project_path_adds_numeric_suffix(tmp_path: Path) -> None:
    base = tmp_path / "demo"
    base.mkdir()
    second = _unique_project_path(base)
    second.mkdir()
    third = _unique_project_path(base)
    assert second.name == "demo-1"
    assert third.name == "demo-2"


def test_scaffold_project_renders_description(tmp_path: Path) -> None:
    description = "a rest api for short links"
    project_path = scaffold_project(
        description,
        output_dir=str(tmp_path),
        template=TEMPLATES["fastapi_api"],
    )
    main_py = project_path / "main.py"
    readme = project_path / "README.md"
    assert main_py.exists()
    assert readme.exists()
    assert description in main_py.read_text(encoding="utf-8")
    assert description in readme.read_text(encoding="utf-8")

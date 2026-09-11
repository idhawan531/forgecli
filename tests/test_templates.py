from forgecli.templates import TEMPLATES, list_templates, select_template


def test_select_template_fastapi() -> None:
    template, matches = select_template("Build a REST API backend service")
    assert template.key == "fastapi_api"
    assert {"rest", "api", "backend", "service"}.issuperset(set(matches))


def test_select_template_vite_react() -> None:
    template, matches = select_template("Create a react dashboard web app")
    assert template.key == "vite_react"
    assert {"react", "dashboard", "web", "app"}.issuperset(set(matches))


def test_select_template_rich_tui() -> None:
    template, matches = select_template("Make a terminal cli tool for productivity")
    assert template.key == "rich_tui"
    assert {"terminal", "cli", "tool"}.issuperset(set(matches))


def test_select_template_tie_falls_back_to_fastapi() -> None:
    template, matches = select_template("build a react api")
    assert template.key == "fastapi_api"
    assert matches == []


def test_select_template_zero_match_falls_back_to_fastapi() -> None:
    template, matches = select_template("something ambiguous with no category")
    assert template.key == "fastapi_api"
    assert matches == []


def test_every_template_directory_exists() -> None:
    for template in list_templates():
        assert template.directory.exists()
        assert template.directory.is_dir()
        assert template.key in TEMPLATES

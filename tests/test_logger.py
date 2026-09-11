from pathlib import Path

from forgecli.logger import log_prompt


def test_log_prompt_creates_file_with_header(tmp_path: Path) -> None:
    log_path = log_prompt(
        "first prompt",
        template_key="fastapi_api",
        next_prompts=["prompt a", "prompt b"],
        log_dir=str(tmp_path),
    )
    content = log_path.read_text(encoding="utf-8")
    assert log_path.exists()
    assert content.startswith("# ForgeCLI Prompt Log")
    assert "## Part 1 — Prompts used to build ForgeCLI" in content
    assert "## Part 2 — Generation log" in content
    assert "first prompt" in content
    assert "Template: fastapi_api" in content
    assert "prompt a" in content


def test_log_prompt_appends_entries(tmp_path: Path) -> None:
    log_prompt(
        "first prompt",
        template_key="fastapi_api",
        next_prompts=["prompt a"],
        log_dir=str(tmp_path),
    )
    log_path = log_prompt(
        "second prompt",
        template_key="rich_tui",
        next_prompts=["prompt b"],
        log_dir=str(tmp_path),
    )
    content = log_path.read_text(encoding="utf-8")
    assert content.count("## 20") == 2
    assert "first prompt" in content
    assert "second prompt" in content
    assert "Template: rich_tui" in content

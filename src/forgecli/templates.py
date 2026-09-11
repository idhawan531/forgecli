"""Template registry and selection helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class Template:
    """Template metadata for project scaffolding."""

    key: str
    title: str
    description: str
    keywords: list[str]
    directory: Path
    preview_file: str
    run_command: str
    install_command: str
    test_command: Optional[str]
    next_prompts: list[str]


_TEMPLATE_ROOT = Path(__file__).parent / "templates_data"

TEMPLATES: dict[str, Template] = {
    "fastapi_api": Template(
        key="fastapi_api",
        title="FastAPI API",
        description="Python REST API with FastAPI, uvicorn, and pytest starter tests.",
        keywords=["api", "rest", "backend", "endpoint", "fastapi", "service", "server", "crud"],
        directory=_TEMPLATE_ROOT / "fastapi_api",
        preview_file="main.py",
        run_command="uvicorn main:app --reload",
        install_command="python -m venv .venv && python -m pip install -r requirements.txt",
        test_command="python -m pytest -q",
        next_prompts=[
            "Add a POST /items endpoint with a Pydantic request model and in-memory storage",
            "Add pytest tests covering every endpoint including error cases",
            "Add a Dockerfile and docker-compose.yml for this FastAPI app",
            "Add request logging middleware and structured error responses",
        ],
    ),
    "vite_react": Template(
        key="vite_react",
        title="Vite + React",
        description="Minimal React app scaffolded with Vite and modern front-end defaults.",
        keywords=["web", "react", "frontend", "ui", "page", "site", "dashboard", "app", "browser"],
        directory=_TEMPLATE_ROOT / "vite_react",
        preview_file="src/App.jsx",
        run_command="npm install && npm run dev",
        install_command="npm install",
        test_command="npm test",
        next_prompts=[
            "Add React Router with a dashboard and settings page",
            "Add API integration with loading and error states",
            "Add component tests with Vitest and React Testing Library",
            "Set up a deploy workflow to GitHub Pages or Vercel",
        ],
    ),
    "rich_tui": Template(
        key="rich_tui",
        title="Rich TUI",
        description="Python terminal app using Typer and Rich components.",
        keywords=["cli", "terminal", "tui", "command line", "console", "script", "tool"],
        directory=_TEMPLATE_ROOT / "rich_tui",
        preview_file="main.py",
        run_command="python main.py",
        install_command="python -m venv .venv && python -m pip install -r requirements.txt",
        test_command="python -m pytest -q",
        next_prompts=[
            "Add interactive prompts to collect user input",
            "Add command options and subcommands for common workflows",
            "Add snapshot-like tests for table/panel rendering helpers",
            "Package this CLI and publish it to PyPI",
        ],
    ),
}


def list_templates() -> list[Template]:
    """Return templates in stable key order."""
    return [TEMPLATES[key] for key in sorted(TEMPLATES)]


def _keyword_in_text(keyword: str, text: str) -> bool:
    return re.search(rf"\b{re.escape(keyword)}\b", text) is not None


def select_template(description: str) -> tuple[Template, list[str]]:
    """Select a template using keyword scores against ``description``.

    On tie or zero matches, this returns the ``fastapi_api`` template.
    """
    lowered = description.lower()
    best_template: Optional[Template] = None
    best_score = -1
    best_matches: list[str] = []
    tie = False

    for template in list_templates():
        matches = [kw for kw in template.keywords if _keyword_in_text(kw, lowered)]
        score = len(matches)

        if score > best_score:
            best_template = template
            best_score = score
            best_matches = matches
            tie = False
        elif score == best_score:
            tie = True

    fallback = TEMPLATES["fastapi_api"]
    if best_template is None or best_score <= 0 or tie:
        return fallback, []
    return best_template, best_matches

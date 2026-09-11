"""Project scaffolding logic for forgecli."""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from forgecli.templates import TEMPLATES, Template

console = Console()

_LEADING_STOPWORDS = {"a", "an", "the", "build", "create", "make", "simple", "minimal"}
_CONNECTIVE_STOPWORDS = {"for", "of", "with", "that", "to", "and", "in", "on"}


def _normalize_slug_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    lowered = ascii_text.strip().lower()
    cleaned = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    return cleaned


def _slugify(description: str) -> str:
    """Convert description text into a concise, filesystem-safe folder name."""
    cleaned = _normalize_slug_text(description)
    words = [word for word in cleaned.split("-") if word]

    while words and words[0] in _LEADING_STOPWORDS:
        words.pop(0)

    words = [word for word in words if word not in _CONNECTIVE_STOPWORDS]

    words = words[:4]
    slug = "-".join(words)[:40].strip("-")
    return slug or "forgecli-project"


def _slugify_explicit_name(name: str) -> str:
    """Sanitize an explicit user-provided project name."""
    return _normalize_slug_text(name) or "forgecli-project"


def _unique_project_path(base_path: Path) -> Path:
    """Return ``base_path``, or a numbered variant if it already exists.

    Appends ``-1``, ``-2``, etc. to the folder name until a path that does
    not yet exist is found, so an existing project is never overwritten.
    """
    if not base_path.exists():
        return base_path

    counter = 1
    while True:
        candidate = base_path.with_name(f"{base_path.name}-{counter}")
        if not candidate.exists():
            return candidate
        counter += 1


def scaffold_project(
    description: str,
    output_dir: str = ".",
    name: Optional[str] = None,
    template: Optional[Template] = None,
) -> Path:
    """Scaffold a project from ``template`` using ``description``.

    Args:
        description: A short, human-readable project description.
        output_dir: Directory in which to create the new project folder.
        name: Optional explicit project name; if omitted, derive from description.
        template: Template metadata and source directory. Defaults to fastapi_api.

    Returns:
        The path to the created project folder.
    """
    selected_template = template or TEMPLATES["fastapi_api"]
    project_name = _slugify_explicit_name(name) if name else _slugify(description)
    project_path = _unique_project_path(Path(output_dir) / project_name)

    console.print(f"[bold blue]Creating project folder[/bold blue] [cyan]{project_path}[/cyan]")
    project_path.mkdir(parents=True)

    context = {
        "description": description,
        "project_name": project_path.name,
        "year": datetime.now(tz=timezone.utc).year,
    }

    environment = Environment(loader=FileSystemLoader(str(selected_template.directory)))
    source_files = sorted(selected_template.directory.rglob("*.j2"))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Rendering template files...", total=len(source_files))
        for source_file in source_files:
            relative_source = source_file.relative_to(selected_template.directory)
            output_relative = relative_source.with_suffix("")
            output_path = project_path / output_relative
            output_path.parent.mkdir(parents=True, exist_ok=True)

            template_obj = environment.get_template(relative_source.as_posix())
            output_path.write_text(template_obj.render(**context), encoding="utf-8")
            progress.advance(task)

    console.print(f"[bold green]Done![/bold green] Project created at [cyan]{project_path}[/cyan]")
    return project_path

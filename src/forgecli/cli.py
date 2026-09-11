"""Command-line interface for forgecli."""

from __future__ import annotations

import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.table import Table

from forgecli.generator import scaffold_project
from forgecli.logger import log_prompt
from forgecli.templates import TEMPLATES, list_templates, select_template

app = typer.Typer(
    name="forgecli",
    help="Forge new project artifacts from a short description.",
    no_args_is_help=True,
)
console = Console()


@app.callback()
def main() -> None:
    """forgecli: forge new project artifacts from a short description."""


def _collect_created_files(project_path: Path) -> list[str]:
    paths = [
        str(path.relative_to(project_path))
        for path in project_path.rglob("*")
        if path.is_file()
    ]
    return sorted(paths)


def _run_template_tests(project_path: Path, test_command: str) -> Optional[bool]:
    command_parts = shlex.split(test_command)
    if command_parts and command_parts[0] == "python":
        command_parts[0] = sys.executable

    try:
        process = subprocess.Popen(
            command_parts,
            cwd=project_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
    except FileNotFoundError as exc:
        console.print(
            f"[yellow]Skipped tests:[/yellow] missing toolchain for '{test_command}': {exc}"
        )
        return None

    assert process.stdout is not None
    console.print(Panel.fit(test_command, title="[bold blue]Running tests[/bold blue]", border_style="blue"))
    for line in process.stdout:
        console.print(line.rstrip())

    return process.wait() == 0


@app.command()
def generate(
    description: str = typer.Argument(
        ...,
        help="A short description of the project you want to scaffold.",
    ),
    output_dir: str = typer.Option(
        ".",
        "--output-dir",
        "-o",
        help="Directory in which to create the new project folder.",
    ),
    name: Optional[str] = typer.Option(
        None,
        "--name",
        "-n",
        help="Optional explicit project folder name.",
    ),
    template: Optional[str] = typer.Option(
        None,
        "--template",
        "-t",
        help="Template key to use. If omitted, forgecli auto-selects one from the description.",
    ),
    run_tests: bool = typer.Option(
        False,
        "--run-tests",
        help="Run template tests after generation when a test command is defined.",
    ),
) -> None:
    """Generate project artifacts from a short DESCRIPTION."""
    if not description.strip():
        console.print("[bold red]Error:[/bold red] description must not be empty.")
        raise typer.Exit(code=1)

    console.print(
        Panel.fit(
            f"[cyan]{description}[/cyan]",
            title="[bold green]Your Description[/bold green]",
            border_style="green",
        )
    )

    if template is not None:
        if template not in TEMPLATES:
            valid = ", ".join(sorted(TEMPLATES))
            console.print(
                f"[bold red]Error:[/bold red] invalid template '{template}'. Valid templates: {valid}"
            )
            raise typer.Exit(code=1)
        selected_template = TEMPLATES[template]
        matched_keywords: list[str] = []
    else:
        selected_template, matched_keywords = select_template(description)
        matched_text = ", ".join(matched_keywords) if matched_keywords else "none (default fallback)"
        console.print(
            Panel.fit(
                f"[bold]Template:[/bold] {selected_template.key}\n"
                f"[bold]Matched keywords:[/bold] {matched_text}",
                title="[bold cyan]Template auto-selection[/bold cyan]",
                border_style="cyan",
            )
        )

    try:
        project_path = scaffold_project(
            description,
            output_dir=output_dir,
            name=name,
            template=selected_template,
        )
    except OSError as exc:
        console.print(f"[bold red]Error:[/bold red] failed to create project files: {exc}")
        raise typer.Exit(code=1) from exc

    try:
        log_path = log_prompt(description, selected_template.key, selected_template.next_prompts)
        console.print(f"[dim]📝 Logged prompt to [underline]{log_path}[/underline][/dim]\n")
    except OSError as exc:
        console.print(
            f"[yellow]Warning:[/yellow] could not write to prompts_log.md: {exc}\n"
        )

    created_files = _collect_created_files(project_path)
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Verifying generated files...", total=len(created_files))
        for _ in created_files:
            time.sleep(0.05)
            progress.advance(task)

    table = Table(title="Created Files", show_header=True, header_style="bold magenta")
    table.add_column("File", style="cyan")
    for filename in created_files:
        table.add_row(filename)
    console.print(table)

    preview_file = project_path / "main.py"
    if not preview_file.exists():
        preview_file = project_path / "src" / "main.jsx"

    if preview_file.exists():
        console.print(
            Panel(
                Syntax(
                    preview_file.read_text(encoding="utf-8"),
                    "python" if preview_file.suffix == ".py" else "jsx",
                    theme="monokai",
                    line_numbers=True,
                ),
                title=f"[bold blue]Preview: {preview_file.relative_to(project_path)}[/bold blue]",
                border_style="blue",
            )
        )

    test_status = "Not run"
    if run_tests:
        if selected_template.test_command is None:
            test_status = "Skipped (template has no test command)"
        else:
            result = _run_template_tests(project_path, selected_template.test_command)
            if result is True:
                test_status = "Passed"
            elif result is False:
                test_status = "Failed"
            else:
                test_status = "Skipped (missing toolchain)"

    next_prompt_text = "\n".join(f"- {prompt}" for prompt in selected_template.next_prompts)
    console.print(
        Panel(
            next_prompt_text,
            title="[bold magenta]Next Copilot prompts[/bold magenta]",
            border_style="magenta",
        )
    )

    console.print(
        Panel.fit(
            f"[bold green]Project created successfully![/bold green]\n"
            f"[cyan]{project_path}[/cyan]\n"
            f"[bold]Template:[/bold] {selected_template.key}\n"
            f"[bold]Tests:[/bold] {test_status}",
            title="[bold green]Success[/bold green]",
            border_style="green",
        )
    )
    if run_tests and test_status == "Failed":
        raise typer.Exit(code=1)


@app.command("templates")
def templates_command() -> None:
    """List available templates and run commands."""
    table = Table(title="Available Templates", show_header=True, header_style="bold magenta")
    table.add_column("Key", style="cyan")
    table.add_column("Title", style="green")
    table.add_column("Description", style="white")
    table.add_column("Run Command", style="yellow")

    for template in list_templates():
        table.add_row(template.key, template.title, template.description, template.run_command)

    console.print(table)


if __name__ == "__main__":
    app()

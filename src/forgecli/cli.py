"""Command-line interface for forgecli."""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
import tempfile
import time
from importlib import metadata
from pathlib import Path
from threading import Thread
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.table import Table

from forgecli import __version__ as _fallback_version
from forgecli.generator import scaffold_project
from forgecli.logger import log_prompt
from forgecli.templates import TEMPLATES, list_templates, select_template

app = typer.Typer(
    name="forgecli",
    help="Forge new project artifacts from a short description.",
    no_args_is_help=True,
)
console = Console()


def _resolve_version() -> str:
    """Return the installed package version, falling back to the source version."""
    try:
        return metadata.version("forgecli")
    except metadata.PackageNotFoundError:
        return _fallback_version


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"forgecli {_resolve_version()}")
        raise typer.Exit(code=0)


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-V",
        help="Show the forgecli version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """forgecli: forge new project artifacts from a short description."""


def _collect_created_files(project_path: Path) -> list[str]:
    paths = [
        str(path.relative_to(project_path))
        for path in project_path.rglob("*")
        if path.is_file()
    ]
    return sorted(paths)


def _preview_lexer(preview_path: Path) -> str:
    """Return the syntax lexer for a generated preview file."""
    return {
        ".py": "python",
        ".jsx": "jsx",
        ".js": "javascript",
        ".ts": "typescript",
    }.get(preview_path.suffix.lower(), "text")


def _project_python(project_path: Path) -> Path:
    """Return the interpreter inside a generated project's local venv."""
    if os.name == "nt":
        return project_path / ".venv" / "Scripts" / "python.exe"
    return project_path / ".venv" / "bin" / "python"


def _run_process(
    project_path: Path,
    command_parts: list[str],
    display_command: str,
    title: str,
    timeout: int,
) -> Optional[bool]:
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
            f"[yellow]Skipped {title.lower()}:[/yellow] missing toolchain for "
            f"'{display_command}': {exc}"
        )
        return None

    assert process.stdout is not None
    console.print(Panel.fit(display_command, title=title, border_style="blue"))

    def stream_output() -> None:
        for line in process.stdout:
            console.print(line.rstrip())

    output_thread = Thread(target=stream_output, daemon=True)
    output_thread.start()
    try:
        return_code = process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
        output_thread.join(timeout=1)
        console.print(
            f"[bold red]{title} timed out after {timeout} seconds and the process "
            "was terminated.[/bold red]"
        )
        return False

    output_thread.join(timeout=1)
    return return_code == 0


def _run_template_install(project_path: Path, install_command: str) -> Optional[bool]:
    """Install generated-project dependencies, including a local Python venv."""
    commands = [part.strip() for part in install_command.split("&&")]
    project_python = _project_python(project_path)

    for index, command in enumerate(commands):
        command_parts = shlex.split(command)
        if index == 0 and command_parts[:3] == ["python", "-m", "venv"]:
            command_parts[0] = sys.executable
        elif index > 0 and command_parts and command_parts[0] == "python":
            command_parts[0] = str(project_python)

        result = _run_process(
            project_path,
            command_parts,
            command,
            "[bold blue]Installing dependencies[/bold blue]",
            timeout=300,
        )
        if result is not True:
            return result

    return True


def _run_template_tests(project_path: Path, test_command: str) -> Optional[bool]:
    """Run generated-project tests with its own interpreter where applicable."""
    command_parts = shlex.split(test_command)
    if command_parts and command_parts[0] == "python":
        command_parts[0] = str(_project_python(project_path))

    return _run_process(
        project_path,
        command_parts,
        test_command,
        "[bold blue]Running tests[/bold blue]",
        timeout=120,
    )


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

    preview_file = project_path / selected_template.preview_file

    if preview_file.exists():
        console.print(
            Panel(
                Syntax(
                    preview_file.read_text(encoding="utf-8"),
                    _preview_lexer(preview_file),
                    theme="monokai",
                    line_numbers=True,
                ),
                title=f"[bold blue]Preview: {preview_file.relative_to(project_path)}[/bold blue]",
                border_style="blue",
            )
        )

    test_status = "Not run"
    if run_tests:
        install_result = _run_template_install(project_path, selected_template.install_command)
        if install_result is False:
            test_status = "Install failed"
        elif install_result is None:
            test_status = "Skipped (missing toolchain)"
        elif selected_template.test_command is None:
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
    if run_tests and test_status in {"Install failed", "Failed"}:
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


@app.command("demo")
def demo(
    output_dir: Optional[str] = typer.Option(
        None,
        "--output-dir",
        "-o",
        help="Directory in which to generate demo projects. Defaults to a fresh temp directory.",
    ),
) -> None:
    """Generate one sample project per registered template for a quick look around."""
    demo_dir = output_dir or tempfile.mkdtemp(prefix="forgecli-demo-")
    Path(demo_dir).mkdir(parents=True, exist_ok=True)

    table = Table(title="Demo Projects", show_header=True, header_style="bold magenta")
    table.add_column("Template", style="cyan")
    table.add_column("Project Path", style="green")
    table.add_column("Files", style="yellow", justify="right")

    for template in list_templates():
        project_path = scaffold_project(
            f"a demo {template.title.lower()} project",
            output_dir=demo_dir,
            name=template.key,
            template=template,
        )
        file_count = len(_collect_created_files(project_path))
        table.add_row(template.key, str(project_path), str(file_count))

    console.print(table)
    console.print(f"\n[bold green]Demo projects written to:[/bold green] {demo_dir}")


if __name__ == "__main__":
    app()

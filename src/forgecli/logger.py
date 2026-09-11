"""Prompt logging utilities for forgecli."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

LOG_FILENAME = "prompts_log.md"
_HEADER = (
    "# ForgeCLI Prompt Log\n\n"
    "## Part 1 — Prompts used to build ForgeCLI\n"
    "_Add your build-time prompts and commit SHAs here._\n\n"
    "## Part 2 — Generation log\n\n"
)


def log_prompt(
    description: str,
    template_key: str,
    next_prompts: list[str],
    log_dir: str = ".",
) -> Path:
    """Append a timestamped generation record to a log file.

    Creates ``prompts_log.md`` (with a header) inside ``log_dir`` if it doesn't
    exist yet, then appends an entry containing the timestamp, description,
    selected template, and suggested next prompts.

    Args:
        description: The description the user passed to ``generate``.
        template_key: The template key used for generation.
        next_prompts: Follow-up suggestions shown to the user.
        log_dir: Directory in which ``prompts_log.md`` lives. Defaults to
            the current working directory.

    Returns:
        The path to the log file.
    """
    log_path = Path(log_dir) / LOG_FILENAME
    is_new = not log_path.exists()

    timestamp = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    entry_lines = [
        f"## {timestamp}",
        f"- Description: {description}",
        f"- Template: {template_key}",
        "- Suggested next prompts:",
    ]
    entry_lines.extend([f"  - {prompt}" for prompt in next_prompts])
    entry = "\n".join(entry_lines) + "\n\n"

    with log_path.open("a", encoding="utf-8") as f:
        if is_new:
            f.write(_HEADER)
        f.write(entry)

    return log_path

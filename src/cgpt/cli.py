"""
cgpt.cli
~~~~~~~~

Command-line entry point for the `cgpt` tool.

This module exposes a Click command group (`main`) with subcommands:

- `cgpt login`  : securely prompt for API key (and optional base URL) and save to the user config.
- `cgpt where`  : print the resolved path of the config file for easy debugging.

The CLI relies on `cgpt.config` for cross-platform config path resolution and
for reading/writing the TOML config file. See that module for details.
"""

from __future__ import annotations

import sys
from typing import Optional

import click

from .config import (
    Config,
    config_path,
    save_config,
)


@click.group(help="cgpt: Tiny ChatGPT terminal client.")
def main() -> None:
    """Root command group.

    Using a Click *group* (instead of a single command) allows the CLI to grow
    naturally with additional subcommands (e.g., `cgpt chat`, `cgpt whoami`)
    without changing the entry point defined in setup.cfg.
    """
    # No body needed — Click uses this as a dispatch group.
    # Subcommands are defined with @main.command(...) below.


@main.command("login")
@click.option(
    "--base-url",
    metavar="URL",
    default=None,
    help="Optional API base URL (leave unset for the default provider endpoint).",
)
def cmd_login(base_url: Optional[str]) -> None:
    """Interactively store credentials in the user config.

    Behavior
    --------
    1) Prompts for the API key with hidden input and confirmation.
    2) Optionally accepts a `--base-url` flag; if omitted, the user is asked
       whether they want to set one, and can enter it interactively.
    3) Writes values to the TOML config at the platform-appropriate path:
         - Linux/macOS: ~/.config/cgpt/config.toml (respects $XDG_CONFIG_HOME)
         - Windows    : %APPDATA%\\cgpt\\config.toml
    4) Sets best-effort restrictive permissions on Unix (handled in save_config).

    Notes
    -----
    - The config file is preferred at runtime. If the config does not exist or
      has no API key, the library falls back to the OPENAI_API_KEY environment
      variable (handled by `resolve_api_key` in cgpt.config).
    - We keep runtime dependencies light by using only Click for UX and
      relying on stdlib I/O + `tomllib` for config parsing elsewhere.
    """
    api_key = click.prompt(
        text="Enter API key",
        hide_input=True,
        confirmation_prompt=True,
        type=str,
    ).strip()

    if base_url is None:
        if click.confirm("Do you want to set a custom base URL?", default=False):
            base_url = click.prompt("Base URL", type=str).strip() or None

    path = save_config(Config(api_key=api_key or None, base_url=base_url or None))
    click.echo(f"✅ Saved credentials to: {path}")


@main.command("where")
def cmd_where() -> None:
    """Print the resolved config file path.

    This is useful for debugging when multiple environments or profiles are used.
    The function does not read or validate the file; it only reports the path
    where `cgpt` expects to find it on this platform.
    """
    click.echo(str(config_path()))


if __name__ == "__main__":
    sys.exit(main())

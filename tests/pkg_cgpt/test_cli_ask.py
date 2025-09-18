import json
from pathlib import Path
from typing import Final
from unittest.mock import patch, MagicMock

import requests
from click.testing import CliRunner, Result
from pytest import MonkeyPatch

from cgpt.config import update_config
from cgpt.cli import main

CFG_SUBPATH: Final[str] = "cfg/config.toml"


def _sandbox(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """Point config lookups to a sandbox directory so tests don't touch real user files."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("APPDATA", str(tmp_path))


def _read_cfg(tmp_path: Path) -> str:
    """Read the sandbox config text file."""
    return (tmp_path / CFG_SUBPATH).read_text(encoding="utf-8")


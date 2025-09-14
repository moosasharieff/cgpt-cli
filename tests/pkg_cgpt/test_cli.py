from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from click.testing import CliRunner
from pytest import MonkeyPatch

from cgpt.cli import main
from cgpt.config import config_path


def _set_sandbox_config_home(monkeypatch, tmp_path: Path) -> None:
    """Redirect config home (XDG/APPDATA) to a sandbox tmp_path for testing."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("APPDATA", str(tmp_path))

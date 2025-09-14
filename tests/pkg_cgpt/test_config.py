from __future__ import annotations

import sys
from pathlib import Path

from pytest import MonkeyPatch

from cgpt.config import Config, config_dir, config_path, load_config


def _redirect_config_home(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """Point config homes to a temporary directory for isolation."""
    # Apply both so the code path under test can pick whichever it uses.
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("APPDATA", str(tmp_path))


def test_config_dir_and_path_on_unix_xdg(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """On Unix, config_dir respects $XDG_CONFIG_HOME/cgpt and config_path appends config.toml."""
    monkeypatch.setattr(sys, "platform", "linux", raising=False)
    _redirect_config_home(tmp_path, monkeypatch)

    cfg_dir: Path = config_dir()
    cfg_path: Path = config_path()

    # Assertions
    assert cfg_dir == Path(tmp_path) / "cgpt"
    assert cfg_path == cfg_dir / "config.toml"


def test_config_dir_and_path_on_windows_appdata(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "platform", "win32", raising=False)
    _redirect_config_home(tmp_path, monkeypatch)

    cfg_dir: Path = config_dir()
    cfg_path: Path = config_path()

    # Assertions
    assert cfg_dir == Path(tmp_path) / "cgpt"
    assert cfg_path == cfg_dir / "config.toml"


def test_load_when_file_missing_returns_empty_config(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """If the TOML file doesn't exist, load_config returns empty values (None)."""
    monkeypatch.setattr(sys, "platform", "linux", raising=False)
    _redirect_config_home(tmp_path, monkeypatch)

    cfg: Config = load_config()
    assert cfg.api_key is None
    assert cfg.base_url is None

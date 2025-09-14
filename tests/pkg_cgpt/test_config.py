from __future__ import annotations

import os
import stat
import sys
from pathlib import Path

import pytest
from pytest import MonkeyPatch

from cgpt.config import Config, config_dir, config_path, load_config, save_config


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


def test_save_and_load_round_trip(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """Saving config creates directory & file; loading returns the same values."""
    monkeypatch.setattr(sys, "platform", "linux", raising=False)
    _redirect_config_home(tmp_path, monkeypatch)

    cfg_in: Config = Config(api_key="abc-def", base_url="https://example.com/v1")
    written_path: Path = save_config(cfg_in)

    assert written_path.exists()
    assert written_path == config_path()

    cfg_out: Config = load_config()
    assert cfg_out.api_key == "abc-def"
    assert cfg_out.base_url == "https://example.com/v1"


@pytest.mark.skipif(
    sys.platform.startswith("win"), reason="chmod checks are Unix-specific"
)
def test_permissions_best_effort_on_unix(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """On Unix, save_config should attempt 0700 for dir and 0600 for file."""
    monkeypatch.setattr(sys, "platform", "linux", raising=False)
    _redirect_config_home(tmp_path, monkeypatch)

    _ = save_config(Config(api_key="sk"))

    cfg_dir: Path = config_dir()
    cfg_path: Path = config_path()
    assert cfg_dir.exists() and cfg_path.exists()

    dir_mode: int = stat.S_IMODE(os.stat(cfg_dir).st_mode)
    file_mode: int = stat.S_IMODE(os.stat(cfg_path).st_mode)

    # Accept exact or stricter bits (umask may influence).
    assert dir_mode & 0o700 == 0o700
    assert file_mode & 0o600 == 0o600

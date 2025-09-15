from __future__ import annotations

import os
import stat
import sys
from pathlib import Path
from typing import Optional

import pytest
from pytest import MonkeyPatch

from cgpt.config import (
    Config,
    config_dir,
    config_path,
    load_config,
    save_config,
    resolve_api_key,
    resolve_base_url,
)


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

    # Identify filesystem permission bits for dir and file
    dir_mode: int = stat.S_IMODE(os.stat(cfg_dir).st_mode)
    file_mode: int = stat.S_IMODE(os.stat(cfg_path).st_mode)

    # Accept exact or stricter bits (umask may influence).
    assert dir_mode & 0o700 == 0o700
    assert file_mode & 0o600 == 0o600


def test_resolve_api_key_prefers_config_over_env(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """If config has an API key, it takes precedence over OPENAI_API_KEY env var."""
    monkeypatch.setattr(sys, "platform", "linux", raising=False)
    _redirect_config_home(tmp_path, monkeypatch)

    monkeypatch.setenv("OPENAI_API_KEY", "sk-from-env")

    _ = save_config(Config(api_key="sk-from-config"))
    resolved: Optional[str] = resolve_api_key()
    assert resolved == "sk-from-config"


def test_resolve_api_key_uses_env_when_no_config(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """If no config file, API key should come from OPENAI_API_KEY."""
    monkeypatch.setattr(sys, "platform", "linux", raising=False)
    _redirect_config_home(tmp_path, monkeypatch)

    monkeypatch.setenv("OPENAI_API_KEY", "sk-env-only")
    resolved: Optional[str] = resolve_api_key()
    assert resolved == "sk-env-only"


def test_resolve_base_url_only_from_config(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """base_url is resolved only from config (no env fallback)."""
    monkeypatch.setattr(sys, "platform", "linux", raising=False)
    _redirect_config_home(tmp_path, monkeypatch)

    monkeypatch.setenv("BASE_URL", "https://env-ignored")
    _ = save_config(Config(api_key="sk", base_url="https://from-config"))
    resolved: Optional[str] = resolve_base_url()
    assert resolved == "https://from-config"


def test_toml_escaping_of_quotes_and_backslashes(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """Values with quotes/backslashes should be escaped on write and restored on load."""
    monkeypatch.setattr(sys, "platform", "linux", raising=False)
    _redirect_config_home(tmp_path, monkeypatch)

    tricky_key: str = r'sk-"weird"\path\with\backslashes'
    tricky_url: str = r'https://api.example.com/v1/"q"?a=1\2'

    written_path: Path = save_config(Config(api_key=tricky_key, base_url=tricky_url))
    content: str = written_path.read_text(encoding="utf-8")

    # Verify the on-disk TOML contains escaped sequences.
    assert 'api_key = "sk-\\"weird\\"\\\\path\\\\with\\\\backslashes"' in content
    assert 'base_url = "https://api.example.com/v1/\\"q\\"?a=1\\\\2"' in content

    # Round-trip: load back to original strings.
    cfg: Config = load_config()
    assert cfg.api_key == tricky_key
    assert cfg.base_url == tricky_url


def test_atomic_write_preserves_symlink(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "platform", "linux", raising=False)
    _redirect_config_home(tmp_path, monkeypatch)

    real = tmp_path / "real-config.toml"
    real.write_text("", encoding="utf-8")
    link = config_path()
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(real)

    save_config(Config(default_model="gpt-5"))
    assert link.is_symlink()  # link still a symlink
    assert 'default_model = "gpt-5"' in real.read_text(encoding="utf-8")

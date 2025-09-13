"""
cgpt.config
~~~~~~~~~~~

Configuration management for the `cgpt` CLI.

- Stores user credentials (API key, optional base_url) in a TOML file.
- Resolves the correct config path across Linux/macOS (XDG) and Windows (APPDATA).
- Provides helpers to save, load, and resolve config values.
- Falls back to the environment variable OPENAI_API_KEY if no config is found.
"""

import os
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Mapping

APP_NAME = "cgpt"
CONFIG_FILE = "config.toml"

# Keys in the TOML file
KEY_API = "api_key"
KEY_BASE_URL = "base_url"


@dataclass
class Config:
    """Dataclass to represent stored configuration values.

    Attributes:
        api_key (Optional[str]): User's API key, or None if unset.
        base_url (Optional[str]): Optional base URL for API, or None if unset.
    """

    api_key: Optional[str] = None
    base_url: Optional[str] = None


def _xdg_config_home() -> Path:
    """Return the base config directory for Linux/macOS.

    Uses $XDG_CONFIG_HOME if set, else falls back to ~/.config.
    """
    home = os.environ.get("XDG_CONFIG_HOME")
    if home:
        return Path(home)
    return Path.home() / ".config"


def _windows_config_home() -> Path:
    """Return the base config directory for Windows.

    Uses %APPDATA% if set, else falls back to ~/AppData/Roaming.
    """
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata)
    return Path.home() / "AppData" / "Roaming"


def config_dir() -> Path:
    """Return the platform-specific directory for cgpt config."""
    if sys.platform.startswith("win"):
        return _windows_config_home() / APP_NAME
    return _xdg_config_home() / APP_NAME


def config_path() -> Path:
    """Return the full path to the cgpt config file (config.toml)."""
    return config_dir() / CONFIG_FILE


def load_config() -> Config:
    """Load config values from TOML file, if it exists.

    Returns:
        Config: A Config object with values populated or None if missing.
    """
    path = config_path()
    if not path.exists():
        return Config()

    with path.open("rb") as f:
        data = tomllib.load(f)

    return Config(
        api_key=data.get(KEY_API) or None,
        base_url=data.get(KEY_BASE_URL) or None,
    )


def save_config(cfg: Config) -> Path:
    """Save the given Config object to a TOML file.

    Creates the config directory if necessary.
    Sets secure permissions on Unix (700 for dir, 600 for file).
    Escapes backslashes/quotes to preserve TOML validity.

    Args:
        cfg (Config): Config values to save.

    Returns:
        Path: The path to the written config file.
    """
    d = config_dir()
    d.mkdir(parents=True, exist_ok=True)
    try:
        if not sys.platform.startswith("win"):
            os.chmod(d, 0o700)
    except Exception:
        pass

    lines = []
    if cfg.api_key is not None:
        lines.append(f'{KEY_API} = "{_escape(cfg.api_key)}"')
    if cfg.base_url is not None:
        lines.append(f'{KEY_BASE_URL} = "{_escape(cfg.base_url)}"')

    content = "\n".join(lines) + ("\n" if lines else "")
    p = config_path()
    p.write_text(content, encoding="utf-8")

    try:
        if not sys.platform.startswith("win"):
            os.chmod(p, 0o600)
    except Exception:
        pass

    return p


def resolve_api_key(env: Optional[Mapping[str, str]] = None) -> Optional[str]:
    """Resolve the API key, preferring config file then OPENAI_API_KEY env.

    Args:
        env (Optional[dict[str, str]]): Optional env mapping for testing.

    Returns:
        Optional[str]: The resolved API key, or None if not found.
    """
    env = env or os.environ
    cfg = load_config()
    if cfg.api_key:
        return cfg.api_key
    return env.get("OPENAI_API_KEY")


def resolve_base_url(env: Optional[dict[str, str]] = None) -> Optional[str]:
    """Resolve the base_url from config, no env fallback.

    Args:
        env (Optional[dict[str, str]]): Included for symmetry; unused.

    Returns:
        Optional[str]: The resolved base_url, or None if not found.
    """
    cfg = load_config()
    return cfg.base_url or None


def _escape(value: str) -> str:
    """Escape quotes and backslashes for safe TOML string values."""
    return value.replace("\\", "\\\\").replace('"', '\\"')

"""
cgpt.config
~~~~~~~~~~~

Configuration management for the `cgpt` CLI.

- Stores user credentials (API key, optional base_url) in a TOML file.
- Resolves the correct config path across Linux/macOS (XDG) and Windows (APPDATA).
- Provides helpers to save, load, and resolve config values.
- Falls back to the environment variable OPENAI_API_KEY if no config is found.
"""

import io
import json
import os
import sys
import tempfile
import time
import tomllib
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Optional, Mapping, Any

APP_NAME = "cgpt"
CONFIG_FILE = "config.toml"

# Keys in the TOML file
KEY_API = "api_key"
KEY_BASE_URL = "base_url"
KEY_DEFAULT_MODEL = "default_model"
KEY_DEFAULT_MODE = "default_mode"


@dataclass
class Config:
    """Dataclass to represent stored configuration values.

    Attributes:
        api_key (Optional[str]): User's API key, or None if unset.
        base_url (Optional[str]): Optional base URL for API, or None if unset.
        default_model (Optional[str]) = Optional ChatGPT Model or None if unset.
        default_mode: (Optional[str]) = "responses" | "chat" or None if unset.
    """

    api_key: Optional[str] = None
    base_url: Optional[str] = None
    default_model: Optional[str] = None
    default_mode: Optional[str] = None


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


def _atomic_write_text(path: Path, data: str, *, follow_symlink: bool = True) -> None:
    """Atomically write `data` to `path`.

    If `path` is a symlink and `follow_symlink` is True (default), write to the
    symlink *target* atomically, keeping the link intact. Otherwise, replace the
    symlink itself.
    """
    # Choose final destination
    dest = path
    if follow_symlink:
        try:
            # `os.path.islink` works even when the link target is missing
            if os.path.islink(path):
                dest = Path(os.path.realpath(path))
        except OSError:
            dest = path  # fall back

    dest.parent.mkdir(parents=True, exist_ok=True)

    # tmp beside the final destination to keep rename atomic on the same FS
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        newline="\n",
        dir=dest.parent,
        prefix=f".{dest.name}.",
        suffix=".tmp",
        delete=False,
    ) as file:
        tmp_path = Path(file.name)
        file.write(data)
        file.flush()
        os.fsync(file.fileno())

    try:
        os.replace(tmp_path, dest)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _dump_toml(data: Mapping[str, Any]) -> str:
    """Serialize a (flat) mapping to TOML using a minimal, safe writer.

    Supports str/bool/int/float scalars. For anything else, values are
    JSON-encoded into a quoted TOML string to remain valid.
    """
    buf = io.StringIO()
    for key, value in data.items():
        if isinstance(value, str):
            buf.write(f'{key} = "{_toml_escape(value)}"\n')
        elif isinstance(value, bool):
            buf.write(f"{key} = {'true' if value else 'false'}\n")
        elif isinstance(value, (int, float)):
            buf.write(f"{key} = {value}\n")
        else:
            # Store unknown types as JSON inside a TOML string
            buf.write(
                f'{key} = "{_toml_escape(json.dumps(value, ensure_ascii=False))}"\n'
            )
    return buf.getvalue()


def _normalize_str(value: Optional[str]) -> Optional[str]:
    """Normalize a string field: treat empty/whitespace-only string as None."""
    if value is None:
        return None
    v = value.strip()
    return v if v else None


def load_config() -> Config:
    """Load configuration from ``config_path()`` (TOML).

    Behavior:
    - If the file does not exist → return an empty/default ``Config()``.
    - If the file is valid TOML → return a ``Config`` populated from keys.
    - If the file is malformed → rename it to ``.bad-<timestamp>`` and return
      an empty/default ``Config()`` (no crash).

    Returns:
        Config: Always a Config instance. Missing/invalid values become ``None``.
    """
    path: Path = config_path()
    if not path.exists():
        return Config()

    try:
        with path.open("rb") as f:
            data: dict = tomllib.load(f)
    except tomllib.TOMLDecodeError:
        # Preserve the broken file for debugging, then fall back to defaults.
        try:
            path.rename(path.with_suffix(path.suffix + f".bad-{int(time.time())}"))
        except OSError:
            # If we can't move it, still continue with defaults.
            pass
        return Config()
    except OSError:
        # IO errors: treat as missing and return defaults.
        return Config()

    def _get_str(key: str) -> Optional[str]:
        val = data.get(key)
        return val if isinstance(val, str) and val.strip() else None

    return Config(
        api_key=_get_str(KEY_API),
        base_url=_get_str(KEY_BASE_URL),
        default_model=_get_str(KEY_DEFAULT_MODEL),
        default_mode=_get_str(KEY_DEFAULT_MODE),
    )


def save_config(cfg: Config) -> Path:
    """Persist the given config to TOML atomically with correct quoting.

    - Creates the config directory if necessary.
    - Uses _dump_toml to ensure strings are quoted (valid TOML).
    - Writes via _atomic_write_text to prevent partial files.
    - Sets secure permissions on Unix (700 dir, 600 file).

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

    # Only include keys that are not None
    data: dict[str, Any] = {}
    if cfg.api_key is not None:
        data[KEY_API] = cfg.api_key
    if cfg.base_url is not None:
        data[KEY_BASE_URL] = cfg.base_url
    if cfg.default_model is not None:
        data[KEY_DEFAULT_MODEL] = cfg.default_model
    if cfg.default_mode is not None:
        data[KEY_DEFAULT_MODE] = cfg.default_mode

    p = config_path()
    _atomic_write_text(p, _dump_toml(data))

    try:
        if not sys.platform.startswith("win"):
            os.chmod(p, 0o600)
    except Exception:
        pass

    return p


def _toml_escape(s: str) -> str:
    """Escape a Python string for TOML basic strings."""
    out = []
    for ch in s:
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif ch == "\b":
            out.append("\\b")
        elif ch == "\t":
            out.append("\\t")
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\f":
            out.append("\\f")
        elif ch == "\r":
            out.append("\\r")
        else:
            # Escape any remaining control chars < 0x20
            if ord(ch) < 0x20:
                out.append(f"\\u{ord(ch):04X}")
            else:
                out.append(ch)
    return "".join(out)


def update_config(**kwargs: Optional[str]) -> Path:
    """Merge provided fields into the existing config and save.

    Accepts only: api_key, base_url, default_model, default_mode.
    Values of None are ignored (existing values remain unchanged).
    Empty strings are normalized to None.
    """
    current = load_config()
    allowed = {"api_key", "base_url", "default_model", "default_mode"}
    cleaned: dict[str, Optional[str]] = {}

    for key, value in kwargs.items():
        if key in allowed and value is not None:
            cleaned[key] = _normalize_str(value)

    new_config = replace(current, **cleaned)
    return save_config(new_config)


def resolve_api_key(env: Optional[Mapping[str, str]] = None) -> Optional[str]:
    """Resolve the API key, preferring config file then OPENAI_API_KEY env.

    Args:
        env (Optional[Mapping[str, str]]): Optional env mapping for testing.

    Returns:
        Optional[str]: The resolved API key, or None if not found.
    """
    env = env or os.environ
    cfg = load_config()
    if cfg.api_key:
        return cfg.api_key
    return env.get("OPENAI_API_KEY")


def resolve_base_url() -> Optional[str]:
    """Resolve the base_url from config (no env fallback).

    Returns:
        Optional[str]: The resolved base_url, or None if not found.
    """
    cfg = load_config()
    return cfg.base_url or None


def _escape(value: str) -> str:
    """Escape quotes and backslashes for safe TOML string values."""
    return value.replace("\\", "\\\\").replace('"', '\\"')

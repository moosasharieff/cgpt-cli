from __future__ import annotations

from pathlib import Path
from typing import Final

from click.testing import CliRunner, Result
from pytest import MonkeyPatch

from cgpt.cli import main
from cgpt.config import config_path, update_config


CFG_SUBPATH: Final[str] = "cgpt/config.toml"


def _set_sandbox_config_home(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """Redirect config home (XDG/APPDATA) to a sandbox tmp_path for testing."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("APPDATA", str(tmp_path))


def test_where_prints_config_path(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """`cgpt where` should print the resolved config path."""
    _set_sandbox_config_home(tmp_path, monkeypatch)

    runner: CliRunner = CliRunner()
    result: Result = runner.invoke(main, ["where"])
    expected: str = str(config_path())

    assert result.exit_code == 0, result.output
    assert expected in result.output


def test_login_writes_api_key_only(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """Login without --base-url writes only api_key to config.toml."""
    _set_sandbox_config_home(tmp_path, monkeypatch)

    runner: CliRunner = CliRunner()
    result: Result = runner.invoke(main, ["login"], input="sk-abc\nsk-abc\nn\n")

    assert result.exit_code == 0, result.output
    assert "Saved credentials to:" in result.output

    cfg_file: Path = tmp_path / CFG_SUBPATH
    assert cfg_file.exists()

    content: str = cfg_file.read_text(encoding="utf-8")
    assert 'api_key = "sk-abc"' in content
    assert "base_url" not in content


def test_login_with_base_url_flag(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """Login with --base-url flag writes both api_key and base_url."""
    _set_sandbox_config_home(tmp_path, monkeypatch)

    runner: CliRunner = CliRunner()
    result: Result = runner.invoke(
        main,
        ["login", "--base-url", "https://example.com/v1"],
        input="sk-xyz\nsk-xyz\n",  # key, confirm
    )

    assert result.exit_code == 0, result.output

    cfg_file: Path = tmp_path / CFG_SUBPATH
    content: str = cfg_file.read_text(encoding="utf-8")

    assert 'api_key = "sk-xyz"' in content
    assert 'base_url = "https://example.com/v1"' in content


def test_login_prompt_sets_base_url_yes(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """Interactive base URL flow: answer 'y' and enter URL."""
    _set_sandbox_config_home(tmp_path, monkeypatch)

    runner: CliRunner = CliRunner()
    result: Result = runner.invoke(
        main,
        ["login"],
        input="sk-123\nsk-123\ny\nhttps://api.local/v1\n",  # key, confirm, 'y', url
    )

    assert result.exit_code == 0, result.output

    cfg_file: Path = tmp_path / CFG_SUBPATH
    content: str = cfg_file.read_text(encoding="utf-8")
    assert 'api_key = "sk-123"' in content
    assert 'base_url = "https://api.local/v1"' in content


def _read_cfg(tmp_path: Path) -> str:
    """Return the text content of the sandbox config file."""
    cfg_file: Path = tmp_path / CFG_SUBPATH
    return cfg_file.read_text(encoding="utf-8")


def test_set_model_only(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """`cgpt set --model ...` writes only `default_model` to config.toml."""
    _set_sandbox_config_home(tmp_path, monkeypatch)

    runner: CliRunner = CliRunner()
    result: Result = runner.invoke(main, ["set", "--model", "gpt-5"])

    assert result.exit_code == 0, result.output

    cfg_text: str = _read_cfg(tmp_path)
    assert 'default_model = "gpt-5"' in cfg_text


def test_set_mode_only(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """`cgpt set --mode responses` writes only `default_mode`."""
    _set_sandbox_config_home(tmp_path, monkeypatch)

    runner: CliRunner = CliRunner()
    result: Result = runner.invoke(main, ["set", "--mode", "responses"])

    assert result.exit_code == 0, result.output
    cfg_text: str = _read_cfg(tmp_path)
    assert 'default_mode = "responses"' in cfg_text


def test_set_both_and_preserve_existing(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """Setting both options updates them and preserves other existing keys."""
    _set_sandbox_config_home(tmp_path, monkeypatch)

    # Prepopulate another field to ensure it is preserved on update
    update_config(api_key="sk-xyz")

    runner: CliRunner = CliRunner()
    result: Result = runner.invoke(
        main,
        ["set", "--model", "gpt-4o-mini", "--mode", "chat"],
    )

    assert result.exit_code == 0, result.output
    cfg_text: str = _read_cfg(tmp_path)
    assert 'api_key = "sk-xyz"' in cfg_text
    assert 'default_model = "gpt-4o-mini"' in cfg_text
    assert 'default_mode = "chat"' in cfg_text


def test_set_requires_at_least_one_option(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """Calling `cgpt set` with no options should raise a usage error."""
    _set_sandbox_config_home(tmp_path, monkeypatch)

    runner: CliRunner = CliRunner()
    result: Result = runner.invoke(main, ["set"])

    assert result.exit_code != 0
    assert "at least one option" in result.output.lower()

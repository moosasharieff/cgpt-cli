from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner, Result
from pytest import MonkeyPatch

from cgpt.cli import main
from cgpt.config import config_path


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

    cfg_file: Path = tmp_path / "cgpt" / "config.toml"
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

    cfg_file: Path = tmp_path / "cgpt" / "config.toml"
    content: str = cfg_file.read_text(encoding="utf-8")

    assert 'api_key = "sk-xyz"' in content
    assert 'base_url = "https://example.com/v1"' in content

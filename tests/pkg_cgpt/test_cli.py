import sys
import subprocess


def run_cgpt(args=None):
    """Helper to run the cgpt CLI and capture output."""
    cmd = [sys.executable, "-m", "cgpt.cli"]
    if args:
        cmd.extend(args)
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout.strip()


def test_cli_default():
    """Running cgpt with no args should greet 'World'."""
    output = run_cgpt([])
    assert "Hello, World!" in output


def test_cli_with_name():
    """Running cgpt with --name should greet the given name."""
    output = run_cgpt(["--name", "Moosa"])
    assert "Hello, Moosa!" in output

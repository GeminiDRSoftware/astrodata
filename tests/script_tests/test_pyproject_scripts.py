"""These tests fetch the scripts from the pyproject.toml file and run them
using ``rst-extract``.
"""

from __future__ import annotations

import functools
import shlex
import subprocess
import sys
from pathlib import Path

import pytest
import tomli


@functools.cache
def scripts() -> dict[str, str]:
    """Fetch the scripts from the pyproject.toml file."""
    pyproject = Path(__file__).parent.parent.parent / "pyproject.toml"
    root_dir = pyproject.parent

    with open(pyproject, "rb") as file:
        data = tomli.load(file)

    scripts = data["tool"]["script_tests"]

    # Need absolute path to ensure these run properly in temporary directories
    scripts = {
        (root_dir / Path(script)).absolute(): options
        for script, options in scripts.items()
    }

    return scripts


def create_rst_extract_command(script: str, options: str | list[str]) -> str:
    """If the script is a Python script, use ``rst-extract``."""
    python_binary = sys.executable
    command = [
        python_binary,
        "-m",
        "rst_extract",
        str(script),
        "--execute",
        "--python-bin",
        str(python_binary),
    ]

    if isinstance(options, str):
        options = shlex.split(options)

    command += options

    return command


@pytest.mark.parametrize("script, options", tuple(scripts().items()))
def test_script_executes(script: str, options: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test the script."""
    # Use temporary directory as the working directory
    command = create_rst_extract_command(script, options)

    monkeypatch.chdir(tmp_path)
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    return_code = result.returncode
    stdout = result.stdout.decode()
    stderr = result.stderr.decode()

    assert return_code == 0
    assert not stderr

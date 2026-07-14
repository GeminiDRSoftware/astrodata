"""These tests fetch the scripts from the pyproject.toml file and run them
using ``rst-extract``.
"""

from __future__ import annotations

import functools
import shlex
import subprocess
import sys
from pathlib import Path
import tempfile

import pytest

from tomllib import load as toml_load

from . import extract_python_code


@functools.cache
def scripts() -> dict[str, str]:
    """Fetch the scripts from the pyproject.toml file."""
    pyproject = Path(__file__).parent.parent.parent / "pyproject.toml"
    root_dir = pyproject.parent

    with open(pyproject, "rb") as file:
        data = toml_load(file)

    scripts = data["tool"]["script_tests"]

    # Need absolute path to ensure these run properly in temporary directories
    scripts = {
        (root_dir / Path(script)).absolute(): options
        for script, options in scripts.items()
    }

    return scripts


@pytest.mark.parametrize("script, options", tuple(scripts().items()))
def test_script_executes(
    script: str, options: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:

    # Read the RST file.
    with open(script, "r") as file:
        rst_content = file.read()

    # Extract the Python code blocks from the RST content and write them
    # to a temporary Python file.
    extracted_code_blocks = extract_python_code(rst_content)
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as temp_file:
        temp_file.write("\n\n".join(extracted_code_blocks))
        temp_file_path = Path(temp_file.name)

    # Use temporary directory as the working directory
    monkeypatch.chdir(tmp_path)

    # Run the temporary Python file using subprocess and capture the output.
    try:
        result = subprocess.run(
                ['python', temp_file_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
    finally:
        # Clean up the temporary file
        temp_file_path.unlink()

    return_code = result.returncode
    stdout = result.stdout.decode()
    stderr = result.stderr.decode()

    print(f"STDERR for {script}:\n{stderr}")

    assert return_code == 0
    assert not stderr

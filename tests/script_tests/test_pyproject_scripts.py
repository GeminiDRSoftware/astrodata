"""These tests fetch the scripts from the pyproject.toml file and run them
using ``rst-extract``.
"""

from pathlib import Path

import pytest
import tomlkit


def scripts() -> dict[str, str]:
    """Fetch the scripts from the pyproject.toml file."""
    pyproject = Path(__file__).parent.parent / "pyproject.toml"

    with open(pyproject, "r") as file:
        data = tomlkit.parse(file.read())

    return data["tool"]["script_tests"]


@pytest.mark.parametrize("script, options", list(scripts().items()))
def test_script(script: str, options: str) -> None:
    """Test the script."""
    options = options.split()
    assert 0 == subprocess.run([script, *options]).returncode

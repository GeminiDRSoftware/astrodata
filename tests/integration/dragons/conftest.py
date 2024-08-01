"""Configures the dragons integration tests.

Testing with DRAGONS
====================

To test with DRAGONS 3.2, conda and nox are required to be installed.

These tests can be specified by running:

```terminal
    nox -s dragons_release_tests
```

Tests should use the dragons mark to be included in the test suite, though this
is not strictly required (TODO: YET).

The DRAGONS tests alone may be selected using either the pytest mark
``dragons`` (``pytest -m dragons``) or the nox session
``dragons_release_tests`` (``nox -s dragons_release_tests``).

+ TODO: Add fixture to set up calibration service for individual tests.
"""

import importlib
from pathlib import Path

import pytest

# Import the LocalDB class from the calibration service module, using importlib
# to avoid undesirable kludging with any of the other dependencies. This is
# probably overkill.
try:
    LocalDB = importlib.import_module("recipe_system.cal_service").LocalDB

except ImportError:
    # This is a bit of a hack, but it's the best way to handle this situation
    # without adding a dependency on the recipe_system package.
    LocalDB = None


def _dragonsrc_generator(location: Path, db_file_path: Path) -> Path:
    """Generate a .dragonsrc file with the given database file path.

    Parameters
    ----------
    location : Path
        The location to save the .dragonsrc file.

    db_file_path : Path
        The path to the database file.

    Returns
    -------
    Path
        The path to the .dragonsrc file.

    Warning
    -------
    This function will overwrite any existing .dragonsrc file at the given
    location. It is meant for tests where that's the desired behavior.
    """
    lines = (
        "[calibs]",
        f"databases = {db_file_path.resolve().absolute()} get store",
    )

    with location.open("w+") as f:
        f.write("\n".join(lines))

    with location.open("r") as f:
        print("\n--- DRAGONSRC CONTENTS ---")
        print(f.read())
        print("^^^ DRAGONSRC CONTENTS ^^^\n")

    return location


@pytest.fixture(autouse=True)
def setup_logging():
    """Set up logging for the tests."""
    gempy = importlib.import_module("gempy")

    gempy.utils.logutils.config(file_name="DRAGONS_log.log")


@pytest.fixture
def calibration_service(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> LocalDB:
    """Fixture to set up the calibration service."""
    # 1) Create a dragonsrc file and assign it to the session environment.
    dragonsrc = tmp_path / ".dragonsrc"
    calibration_path = tmp_path / "calibrations.db"

    _ = _dragonsrc_generator(dragonsrc, calibration_path)

    monkeypatch.setenv("DRAGONSRC", str(dragonsrc))

    # 2) Return the calibration service.
    cal_service = importlib.import_module("recipe_system.cal_service")
    cal_service.load_config(str(dragonsrc))

    caldb = cal_service.LocalDB(str(calibration_path), force_init=True)
    # caldb.init(wipe=True)

    return caldb

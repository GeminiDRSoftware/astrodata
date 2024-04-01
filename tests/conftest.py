"""Configuration for astrodata tests (using pytest)."""

import importlib
import os

import pytest


# Reload the module for each test, to avoid problems with factory state.
@pytest.fixture(autouse=True)
def reload_astrodata():
    """Reload the astrodata module."""
    importlib.reload(importlib.import_module("astrodata"))


@pytest.fixture(scope="session", autouse=True)
def assign_test_cache(tmp_path_factory):
    """Assign a temporary cache directory for testing."""
    # Set ASTRODATA_TEST to the temporary directory if it is not already set.
    result = None
    tmpdir = tmp_path_factory.mktemp(".testing_cache")

    if not (result := os.environ.get("ASTRODATA_TEST")):
        os.environ["ASTRODATA_TEST"] = os.path.join(
            tmpdir, "archive_downloads"
        )

    yield

    # Unset the ASTRODATA_TEST environment variable (in case python session
    # lasts beyond pytest lifetime for some reason).
    if not result:
        os.environ.pop("ASTRODATA_TEST")

    else:
        os.environ["ASTRODATA_TEST"] = result

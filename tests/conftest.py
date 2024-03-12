"""Configuration for astrodata tests (using pytest)."""
import importlib

import pytest


# Reload the module for each test, to avoid problems with factory state.
@pytest.fixture(autouse=True)
def reload_astrodata():
    """Reload the astrodata module."""
    importlib.reload(importlib.import_module("astrodata"))

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

import os


import pytest


@pytest.fixture
def use_temporary_working_directory(tmp_path):
    """Change the working directory to a temporary directory."""
    # TODO: Remove this fixture --- it is managed by nox now.
    return os.getcwd()

    original_directory = os.getcwd()
    # tmp_path = tmp_path_factory.mktemp("working_directory")
    os.chdir(tmp_path)

    yield tmp_path

    os.chdir(original_directory)

    # Report the location of the temporary directory in case the test outputs
    # need to be checked.
    print(f"Temporary directory: {tmp_path}")

"""File for running nox sessions.

TODO:
- [x] Add nox session for dragons environment creation.
- [x] Add nox session for running unit tests.
    - [ ] Get the dependencies from the poetry.lock file.
"""

import os
from pathlib import Path
import functools


import nox


# Nox configuration
# Default nox sessions to run when executing "nox" without session
# specifications (i.e., without the -s flag).
nox.options.sessions = ["unit_tests", "coverage"]


class SessionVariables:
    """Session variables for the nox sessions."""

    # Useful paths -- access through static methods
    _test_dir = Path(__file__).parent / "tests"
    _noxfile_dir = Path(__file__).parent

    # DRAGONS download channel
    dragons_channel = "http://astroconda.gemini.edu/public"
    dragons_conda_channels = ["conda-forge", dragons_channel]

    # Poetry install options
    poetry_install_options = ["--with", "test", "--without", "dev,docs"]

    # pytest options for sessions
    pytest_options = ["--cov=astrodata", "--cov-report=term-missing"]

    dragons_tests_path = os.path.join(_test_dir, "integration/dragons")
    dragons_pytest_options = pytest_options + [dragons_tests_path]

    # TODO: Unit tests should probably get their own tag, or the way this is
    # handled should be updated.
    unit_pytest_options = pytest_options + ["-m", "not dragons"]

    # Python versions
    python_versions = [
        "3.10",
        "3.11",
        "3.12",
    ]

    @staticmethod
    def noxfile_dir() -> str:
        """Get the directory of the noxfile."""
        return SessionVariables._noxfile_dir

    @staticmethod
    def test_dir() -> str:
        return SessionVariables._test_dir

    # This class is not meant to be instantiated. It is just used as a
    # namespace.
    def __new__(cls):
        raise NotImplementedError("This class should not be instantiated.")


def dragons_isolated_dir(func):
    """Create an isolated directory and environment for the dragons tests.

    This wraps a function and creates a temporary directory and sets
    some DRAGONS environment variables.
    """

    @functools.wraps(func)
    def wrapper(session: nox.Session) -> None:
        tmp_path = session.create_tmp()
        with session.chdir(tmp_path):
            # Set the DRAGONSRC environment variable.
            os.environ["DRAGONSRC"] = tmp_path / "dragonsrc"

            # Create the DRAGONSRC file.
            dragonsrc_contents = f"""
            [calibs]
            databases = {tmp_path} get store
            """

            # Remove leading and trailing whitespace from each line and remove
            # empty lines.
            dragonsrc_contents = "\n".join(
                line.strip() for line in dragonsrc_contents.split("\n") if line
            )

            with open(os.environ["DRAGONSRC"], "w+") as f:
                f.write(dragonsrc_contents)

            # Create the calibrations database file.
            with open(tmp_path / "calibrations.db", "w+") as f:
                pass

            # Run the function.
            result = func(session)

        return result

    return wrapper


def get_poetry_dependencies(session: nox.Session, only: str = ""):
    """Get the dependencies from the poetry.lock file.

    This assumes poetry is installed in the session.

    Arguments
    ---------
    session : nox.sessions.Session
        The nox session object.

    only : str, list, optional
        If provided, only return the dependencies that match the provided
        string or strings.
    """
    command = ["poetry", "show"]

    if only:
        command.extend(["--only", only])

    out = session.run(
        *command,
        external=True,
        silent=True,
    )

    # Poetry uses (!) to indicate a package is not installed when terminal
    # colors are not available to it (e.g., in a nox session). Need to remove
    # these. They are inconsistent from line to line.
    out = out.replace("(!)", "")

    package_strs = out.splitlines()
    package_columns = [line.split() for line in package_strs]
    packages = [
        "==".join([column[0], column[1]]) for column in package_columns
    ]

    return packages


def install_test_dependencies(session: nox.Session) -> None:
    """Install the test dependencies from the poetry.lock file."""
    packages = get_poetry_dependencies(session, "main,test")

    session.install(*packages)


@nox.session(venv_backend="conda", python="3.10")
@dragons_isolated_dir
def dragons_release_tests(session: nox.Session) -> None:
    """Run the tests for the DRAGONS conda package."""
    # Fetch test dependencies from the poetry.lock file.
    install_test_dependencies(session)

    # Install the DRAGONS package, and ds9 for completeness.
    session.conda_install(
        "dragons==3.2",
        channel=SessionVariables.dragons_conda_channels,
    )

    session.conda_install(
        "ds9",
        channel=SessionVariables.dragons_conda_channels,
    )

    session.install("-e", f"{SessionVariables.noxfile_dir()}", "--no-deps")

    # Positional arguments after -- are passed to pytest.
    pos_args = session.posargs

    session.run(
        "pytest",
        *SessionVariables.dragons_pytest_options,
        *pos_args,
    )


@nox.session(python=SessionVariables.python_versions)
def unit_tests(session: nox.Session) -> None:
    """Run the unit tests."""
    install_test_dependencies(session)
    session.install(".")

    # Positional arguments after -- are passed to pytest.
    pos_args = session.posargs

    # Run the tests. Need to pass arguments to pytest.
    session.run(
        "pytest",
        *SessionVariables.unit_pytest_options,
        *pos_args,
    )


@nox.session
def coverage(session: nox.Session) -> None:
    """Run the tests and generate a coverage report."""
    # Install the test dependencies.
    install_test_dependencies(session)

    # Generate the coverage report.
    session.run("coverage", "report", "--show-missing")

    # Generate the HTML report.
    session.run("coverage", "html")


# `--session`/`-s` flag. For example, `nox -s dragons_calibration`.
#
# Important note --- these tests should be run as a part of the routine tests
# above. They are separated here for ease of diagnosis for common problems.
@nox.session(venv_backend="conda", python="3.10")
@dragons_isolated_dir
def dragons_calibration(session: nox.Session) -> None:
    """Run the calibration tests."""
    session.conda_install(
        "dragons==3.2",
        channel=SessionVariables.dragons_conda_channels,
    )

    install_test_dependencies(session)

    session.install("-e", ".", "--no-deps")

    # Positional arguments after -- are passed to pytest.
    pos_args = session.posargs

    # Run the tests. Need to pass arguments to pytest.
    session.run(
        "pytest",
        "tests/integration/dragons/test_calibration_setup.py",
        *pos_args,
    )

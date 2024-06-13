"""File for running nox sessions.

TODO:
- [x] Add nox session for dragons environment creation.
- [x] Add nox session for running unit tests.
    - [ ] Get the dependencies from the poetry.lock file.
"""

import nox


class SessionVariables:
    """Session variables for the nox sessions."""

    # DRAGONS download channel
    dragons_channel = "http://astroconda.gemini.edu/public"
    dragons_conda_channels = ["conda-forge", dragons_channel]

    # Poetry install options
    poetry_install_options = ["--with", "test", "--without", "dev,docs"]

    # pytest options for sessions
    pytest_options = ["--cov=astrodata", "--cov-report=term-missing"]

    dragons_pytest_options = pytest_options + ["-m", "dragons"]

    # TODO: Unit tests should probably get their own tag, or the way this is
    # handled should be updated.
    unit_pytest_options = pytest_options + ["-m", "not dragons"]

    # Python versions
    python_versions = [
        "3.10",
        "3.11",
        "3.12",
    ]

    # This class is not meant to be instantiated. It is just used as a
    # namespace.
    def __new__(cls):
        raise NotImplementedError("This class should not be instantiated.")


def get_poetry_dependencies(session, only=""):
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


def install_test_dependencies(session):
    """Install the test dependencies from the poetry.lock file."""
    packages = get_poetry_dependencies(session, "test")

    session.install(*packages)


@nox.session(venv_backend="conda", python="3.10")
def dragons_release_tests(session):
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

    session.install(".", "--no-deps")

    # Positional arguments after -- are passed to pytest.
    pos_args = session.posargs

    session.run(
        "pytest",
        *SessionVariables.dragons_pytest_options,
        *pos_args,
    )


@nox.session(python=SessionVariables.python_versions)
def unit_tests(session):
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
def coverage(session):
    """Run the tests and generate a coverage report."""
    # Install the test dependencies.
    install_test_dependencies(session)

    # Run the tests with coverage.
    # session.run("pytest", "--cov=src", *SessionVariables.unit_pytest_options)

    # Generate the coverage report.
    session.run("coverage", "report", "--show-missing")

    # Generate the HTML report.
    session.run("coverage", "html")

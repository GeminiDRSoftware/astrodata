"""File for running nox sessions.

TODO:
- [x] Add nox session for dragons environment creation.
- [x] Add nox session for running unit tests.
    - [x] Get the dependencies from the poetry.lock file.
- [ ] Test the astrodata pip installations using devpi.
- [ ] Test release builds.
"""

from pathlib import Path
from typing import ClassVar

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
    dragons_conda_channels: ClassVar[list[str]] = [
        "conda-forge",
        dragons_channel,
    ]
    dragons_github_url = "https://github.com/GeminiDRSoftware/DRAGONS.git"

    # Poetry install options
    poetry_install_options: ClassVar[list[str]] = [
        "--with",
        "test",
        "--without",
        "dev,docs",
    ]

    # pytest options for sessions
    pytest_options = ["--cov=astrodata", "--cov-report=term-missing"]

    dragons_tests_path = _test_dir / "integration/dragons"
    dragons_pytest_options = pytest_options + [str(dragons_tests_path)]

    unit_tests_path = _test_dir / "unit"
    unit_pytest_options = pytest_options + [str(unit_tests_path)]

    # Python versions
    python_versions: ClassVar[list[str]] = [
        "3.10",
        "3.11",
        "3.12",
    ]

    @staticmethod
    def noxfile_dir() -> Path:
        """Return the path of the directory containing this file."""
        return SessionVariables._noxfile_dir

    @staticmethod
    def test_dir() -> Path:
        """Return the test directory path."""
        return SessionVariables._test_dir

    def __new__(cls) -> None:
        """Just catches accidental invocations."""
        message = "This class should not be instantiated."
        raise NotImplementedError(message)


def get_poetry_dependencies(session: nox.Session, only: str = "") -> None:
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
    session.install("--upgrade", "pip")
    packages = get_poetry_dependencies(session, "main,test")

    session.install(*packages)


@nox.session(venv_backend="conda", python="3.10")
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

    _ = session.run(
        "pytest",
        *SessionVariables.dragons_pytest_options,
        *pos_args,
    )


@nox.session(venv_backend="conda", python="3.10")
def dragons_dev_tests(session: nox.Session) -> None:
    """Run the tests for the DRAGONS conda package."""
    # Fetch test dependencies from the poetry.lock file.
    install_test_dependencies(session)

    # Need to install sectractor as a conda package. Everything else in this
    # install should be via pip, not conda.
    session.conda_install(
        "astromatic-source-extractor",
        channel=SessionVariables.dragons_conda_channels,
    )

    session.conda_install(
        "ds9",
        channel=SessionVariables.dragons_conda_channels,
    )

    # Install the DRAGONS package, and ds9 for completeness.
    tmp_dir = Path(session.create_tmp())

    with session.cd(tmp_dir):
        # Get cal_manager and obs_db_manager. GeminiObsDB is a dependency of
        # GeminiCalMgr, and must be installed first.
        session.install(
            "git+https://github.com/GeminiDRSoftware/GeminiObsDB@v1.0.29",
        )

        session.install(
            "git+https://github.com/GeminiDRSoftware/GeminiCalMgr@v1.1.24",
        )

        # Clone the DRAGONS repository
        # Only run this if the directory does not exist. Otherwise, it will try
        # to install it even if re-using the session environemnt.
        if not Path("dragons").exists():
            session.run(
                "git",
                "clone",
                SessionVariables.dragons_github_url,
                "dragons",
                external=True,
            )

        else:
            print("DRAGONS repository already exists. Skipping clone.")

        with session.cd("dragons"):
            # Install the DRAGONS package
            session.install("-e", ".")

    session.install("-e", f"{SessionVariables.noxfile_dir()}", "--no-deps")

    # Positional arguments after -- are passed to pytest.
    pos_args = session.posargs

    _ = session.run(
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
    _ = session.run("pytest", *SessionVariables.unit_pytest_options, *pos_args)


@nox.session
def coverage(session: nox.Session) -> None:
    """Run the tests and generate a coverage report."""
    # Install the test dependencies.
    install_test_dependencies(session)

    # Generate the coverage report.
    _ = session.run("coverage", "report", "--show-missing")

    # Generate the HTML report.
    _ = session.run("coverage", "html")


# `--session`/`-s` flag. For example, `nox -s dragons_calibration`.
#
# Important note --- these tests should be run as a part of the routine tests
# above. They are separated here for ease of diagnosis for common problems.
@nox.session(venv_backend="conda", python="3.10")
def dragons_calibration(
    session: nox.Session,
    dragonsrc_path: Path | None = None,
) -> None:
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
    _ = session.run(
        "pytest",
        "tests/integration/dragons/test_calibration_setup.py",
        *pos_args,
        env={"DRAGONSRC": str(dragonsrc_path)},
    )

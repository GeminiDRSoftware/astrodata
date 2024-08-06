"""File for running nox sessions.

TODO:
- [x] Add nox session for dragons environment creation.
- [x] Add nox session for running unit tests.
    - [x] Get the dependencies from the poetry.lock file.
- [ ] Test the astrodata pip installations using devpi.
    - [x] Get a devpi server running.
    - [x] Configure it to accept uploads.
    - [x] Run sessions using the server as the installation source to mimic a
          release.
- [ ] Test release builds.
"""

import functools
import subprocess
import sys
import time
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
    dragons_dev_packages = [
        "astropy>=6",
        "astroquery",
        "matplotlib",
        "numpy<2",
        "psutil",
    ]

    dragons_venv_params = [
        v for channel in dragons_conda_channels for v in ("-c", channel)
    ]
    dragons_venv_params += ["--override-channels"]

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

    # devpi server information
    devpi_host = "localhost"
    devpi_initial_port = 1420

    @classmethod
    @functools.cache
    def devpi_port(self) -> int:
        """Return the devpi port."""
        # Find a free port
        start_port = self.devpi_initial_port

        # Just in case there's a bug/issue, only try a specific number of times.
        attempts = 1000

        from contextlib import closing
        import socket

        # Use python to test if the port is available.
        with closing(
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ) as sock:
            for _ in range(attempts):
                if sock.connect_ex(("localhost", start_port)) != 0:
                    break

                start_port += 1

        return start_port

    @classmethod
    def devpi_url(cls) -> str:
        """Return the devpi URL."""
        return f"http://{cls.devpi_host}:{cls.devpi_port()}/"

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


class DevpiServerManager:
    """Context manager that will start and stop a devpi server."""

    index_url: str | None
    server_process: subprocess.Popen | None
    session: nox.Session
    tmp_dir: Path | None

    active_servers: ClassVar[dict[int, "DevpiServerManager"]] = {}

    # Host/port info
    host: ClassVar[str] = SessionVariables.devpi_host
    port: ClassVar[int] = SessionVariables.devpi_port()
    url: ClassVar[str] = SessionVariables.devpi_url()

    def __init__(
        self, session: nox.Session, tmp_dir: Path | None = None
    ) -> None:
        """Initialize the context manager."""
        self.session = session
        self.tmp_dir = tmp_dir

        # Initialize other attributes.
        self.index_url = None
        self.server_process = None

        # Initialization methods
        self.configure_devpi_tmp_dir()

        # Register the server
        self.active_servers[self.port] = self

    def __enter__(self):
        """Start the devpi server."""
        session = self.session

        install_test_dependencies(session, poetry_groups=["build_test"])

        self.generate_config_file()
        self.start_devpi_server()

    def __exit__(self, exc_type, exc_value, traceback):
        """Stop the devpi server."""
        self.stop_devpi_server()

    def configure_devpi_tmp_dir(self):
        """Configure the temporary directory for the devpi server."""
        session = self.session
        tmp_dir = self.tmp_dir

        if tmp_dir is None:
            temp_dir = (Path(session.create_tmp()) / "devpi").absolute()

        temp_dir.mkdir()

        self.tmp_dir = temp_dir

    def generate_config_file(self):
        """Generate the devpi configuration file."""
        session = self.session
        tmp_dir = self.tmp_dir
        port = self.port

        with session.cd(tmp_dir):
            session.run("devpi-init", "--serverdir", ".")
            session.run(
                "devpi-gen-config",
                "--serverdir",
                tmp_dir,
                "--port",
                str(port),
            )

    def wait_for_devpi_startup(self, session: nox.Session) -> bool:
        """Wait for the devpi server to start. This assumes that the server
        has been started, there is no check for the server process itself.

        It performs a curl request to the devpi server to check if it is
        running, and it will pass for any kind of response.
        """
        timeout = 25
        started = False

        for check in range(1, timeout + 1):
            session.log(f"Checking for devpi server... {check}/{timeout}")

            try:
                _ = session.run(
                    "curl",
                    SessionVariables.devpi_url(),
                    silent=True,
                    external=True,
                )
                started = True
                break

            except nox.command.CommandFailed:
                time.sleep(1)

        # If the process has failed, show the output and stderr
        print(f"Server process: {self.server_process.pid}")

        return started

    def check_devpi_server_process(self):
        """Check that the devpi server process is running without issue."""
        server_process = self.server_process
        session = self.session
        started = self.wait_for_devpi_startup(session)

        if server_process.poll() is not None or not started:
            stdout, stderr = server_process.communicate()
            session.log(f"stdout: {stdout}")
            session.log(f"stderr: {stderr}")
            raise RuntimeError("Devpi server failed to start.")

    def start_devpi_server(self):
        """Start the devpi server."""
        session = self.session
        tmp_dir = self.tmp_dir
        port = self.port

        self.server_process = subprocess.Popen(
            ["devpi-server", "--serverdir", tmp_dir, "--port", str(port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Wait for the server to start
        session.log("Waiting for devpi server to start...")

        # If the process has failed, show the output and stderr
        self.check_devpi_server_process()

        print(f"Server process: {self.server_process.pid}")

        self.configure_devpi_client()

    def configure_devpi_client(self):
        """Configure the devpi client."""
        session = self.session
        port = self.port

        # Configure the devpi client
        session.run("devpi", "use", f"http://localhost:{port}")
        session.run("devpi", "user", "-c", "testuser", "password=123")
        session.run("devpi", "login", "testuser", "--password=123")
        session.run("devpi", "index", "-c", "dev", "bases=root/pypi")
        session.run("devpi", "use", "-l")
        session.run("devpi", "use", "testuser/dev")

        # Set the pip index URL
        session.env["PIP_INDEX_URL"] = (
            f"http://localhost:{port}/testuser/dev/+simple/"
        )

        self.index_url = f"http://localhost:{port}/testuser/dev/+simple/"

    def stop_devpi_server(self):
        """Stop the devpi server."""
        session = self.session
        tmp_dir = self.tmp_dir

        session.log("Stopping devpi server...")

        if hasattr(self, "server_process") and self.server_process is not None:
            self.server_process.terminate()
            self.server_process.wait()

        if tmp_dir is not None and tmp_dir.exists():
            session.run("rm", "-rf", tmp_dir, external=True)

        del self.active_servers[self.port]


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


def install_test_dependencies(
    session: nox.Session,
    packages: list[str] | None = None,
    poetry_groups: list[str] | None = None,
) -> None:
    """Install the test dependencies from the poetry.lock file.

    Arguments
    ---------
    session : nox.sessions.Session
        The nox session object.

    packages : list, optional
        A list of packages to install. If provided, this will be used instead
        of the poetry.lock file.

    poetry_groups : list, optional
        A list of poetry groups to install. If provided, this will be used
        instead of the default groups (main, test). Please note that the
        main group is ignored if not provided in the list. For example,

        .. code-block::python

            poetry_groups = ["test"]

        will install only the test dependencies, not |astrodata|.

        Also, an empty list will still install the default groups (main, test).
    """
    # If using venv, upgrade pip first. If in a conda env, this is not needed
    # because of nuances with the installed versions.
    if session.venv_backend == "venv":
        session.install("--upgrade", "pip")

    # Report the pip version
    session.run("python", "-m", "pip", "--version")

    # Get the dependencies from the poetry.lock file if no packages are provided.
    if not packages:
        groups = ["main", "test"] if not poetry_groups else poetry_groups
        packages = get_poetry_dependencies(session, ",".join(groups))

    session.install(*packages)


def apply_macos_config(session: nox.Session) -> None:
    """Apply macOS specific configurations."""
    # This configuration is to ensure that conda uses the correct architecture
    # (x86_64) on M-series Macs.
    if sys.platform == "darwin":
        session.env["CONDA_SUBDIR"] = "osx-64"
        session.run("conda", "config", "--env", "--set", "subdir", "osx-64")

        print("Setting CONDA_SUBDIR to osx-64.")


@nox.session(
    venv_backend="conda",
    venv_params=SessionVariables.dragons_venv_params,
    python="3.10",
)
def dragons_release_tests(session: nox.Session) -> None:
    """Run the tests for the DRAGONS conda package."""
    apply_macos_config(session)

    # Fetch test dependencies from the poetry.lock file.
    install_test_dependencies(session)

    # Install the DRAGONS package, and ds9 for completeness.
    session.conda_install(
        "dragons==3.2",
        "ds9",
        channel=SessionVariables.dragons_conda_channels,
    )

    # Need to downgrade numpy because of DRAGONS issue 464
    # https://github.com/GeminiDRSoftware/DRAGONS/issues/464
    session.conda_install("numpy<2")

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
    apply_macos_config(session)

    # Fetch test dependencies from the poetry.lock file.
    install_test_dependencies(session)
    install_test_dependencies(
        session, packages=SessionVariables.dragons_dev_packages
    )

    # Need to install sectractor as a conda package. Everything else in this
    # install should be via pip, not conda.
    session.conda_install(
        "astromatic-source-extractor",
        "ds9",
        channel=SessionVariables.dragons_conda_channels,
    )

    # Install the DRAGONS package, and ds9 for completeness.
    tmp_dir = Path(session.create_tmp())

    # Get cal_manager and obs_db_manager. GeminiObsDB is a dependency of
    # GeminiCalMgr, and must be installed first.
    session.install(
        "git+https://github.com/GeminiDRSoftware/GeminiObsDB@v1.0.29",
    )

    session.install(
        "git+https://github.com/GeminiDRSoftware/GeminiCalMgr@v1.1.24",
    )

    with session.cd(tmp_dir):
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

            # Completely remove the dragons/astrodata directory. This is to
            # ensure that the package is installed from the source code and
            # catch any relative import issues.
            session.run("rm", "-rf", "dragons/astrodata", external=True)

        else:
            print("DRAGONS repository already exists. Skipping clone.")

        with session.cd("dragons"):
            # Install the DRAGONS package
            session.install("-e", ".")

    # Need to downgrade numpy because of DRAGONS issue 464
    # https://github.com/GeminiDRSoftware/DRAGONS/issues/464
    session.conda_install("numpy<2")

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


@nox.session(python=SessionVariables.python_versions)
def unit_tests_build(session: nox.Session) -> None:
    """Run the unit tests using the build version of the package."""
    # Install the package from the devpi server
    install_test_dependencies(session, poetry_groups=["test"])

    # Install the package from the devpi server
    session.install(
        "astrodata",
        "--index-url",
        SessionVariables.devpi_url(),
    )

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


@nox.session
def docs(session: nox.Session) -> None:
    """Build the documentation."""
    # Install the documentation dependencies.
    install_test_dependencies(session, poetry_groups=["main", "docs"])

    session.install("-e", ".", "--no-deps")

    # Build the documentation.
    # TODO(teald): Add nitpicky flag to fix warnings. -- Issue #42
    target = Path("_build")
    _ = session.run("rm", "-rf", target, external=True)
    _ = session.run("sphinx-build", "docs", target)


def use_devpi_server(func):
    @functools.wraps(func)
    def wrapper(session, *args, **kwargs):
        # Create a temporary directory for the devpi server
        with DevpiServerManager(session):
            func(session, *args, **kwargs)

    return wrapper


@nox.session(python=SessionVariables.python_versions)
@use_devpi_server
def build_tests(session: nox.Session) -> None:
    """Builds the library, 'uploads' it to a devpi server, then installs and
    tests it in an isolated environment.
    """
    # Build the package and upload it to the devpi server
    tmp_build_dir = Path(session.create_tmp()) / "build"
    tmp_build_dir.mkdir()

    _ = session.run(
        "poetry",
        "build",
        f"--output={tmp_build_dir}",
        external=True,
    )

    # Shows available indexes
    poetry_config_env_vars = {
        "POETRY_REPOSITORIES_BUILD_TEST_URL": session.env["PIP_INDEX_URL"],
        "POETRY_REPOSITORIES_BUILD_TEST_USERNAME": "testuser",
        "POETRY_REPOSITORIES_BUILD_TEST_PASSWORD": "123",
    }

    _result = session.run(
        "poetry",
        "publish",
        "--repository",
        "build_test",
        f"--dist-dir={tmp_build_dir.absolute()}",
        "--no-cache",
        external=True,
        env=poetry_config_env_vars,
    )


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

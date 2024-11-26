"""File for running nox sessions."""

from __future__ import annotations

import functools
import os
import socket
import subprocess
import sys
import time
from contextlib import closing
from pathlib import Path
from typing import ClassVar

import nox
import tomllib

# Nox configuration
# Default nox sessions to run when executing "nox" without session
# specifications (i.e., without the -s flag).
nox.options.sessions = ["unit_tests", "coverage"]
nox.options.error_on_external_run = True


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
    def devpi_port(cls) -> int:
        """Return the devpi port."""
        # Find a free port
        start_port = cls.devpi_initial_port

        # Just in case there's a bug/issue, only try a specific number of
        # times.
        attempts = 1000

        # Use python to test if the port is available.
        af_inet, sock_stream = socket.AF_INET, socket.SOCK_STREAM
        with closing(socket.socket(af_inet, sock_stream)) as sock:
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


class DevpiServerError(RuntimeError):
    """Exception for devpi server errors."""

    def __init__(self, message: str) -> None:
        """Initialize the error."""
        super().__init__(f"Problem with devpi server: {message}")


class DevpiServerManager:
    """Context manager that will start and stop a devpi server."""

    index_url: str | None
    server_process: subprocess.Popen | None
    session: nox.Session
    tmp_dir: Path | None

    active_servers: ClassVar[dict[int, DevpiServerManager]] = {}

    # Host/port info
    host: ClassVar[str] = SessionVariables.devpi_host
    port: ClassVar[int] = SessionVariables.devpi_port()
    url: ClassVar[str] = SessionVariables.devpi_url()

    def __init__(
        self,
        session: nox.Session,
        tmp_dir: Path | None = None,
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
        """Wait for the devpi server to start.

        This assumes that the server has been started, there is no check for
        the server process itself.  It performs a curl request to the devpi
        server to check if it is running, and it will pass for any kind of
        response.
        """
        timeout = 25
        started = False

        for check in range(1, timeout + 1):
            session.log(f"Checking for devpi server... {check}/{timeout}")

            try:
                session.run(
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
        session.log(f"Server process: {self.server_process.pid}")

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

            message = "Devpi server failed to start."
            raise DevpiServerError(message)

    def start_devpi_server(self):
        """Start the devpi server."""
        session = self.session
        tmp_dir = self.tmp_dir
        port = self.port

        # Check that the server is available.abs
        result = session.run(
            "which",
            "devpi-server",
            silent=True,
            external=True,
        )

        devpi_server_path = result.strip()

        self.server_process = subprocess.Popen(
            [devpi_server_path, "--serverdir", tmp_dir, "--port", str(port)],  # noqa: S603
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Wait for the server to start
        session.log("Waiting for devpi server to start...")

        # If the process has failed, show the output and stderr
        self.check_devpi_server_process()

        session.log(f"Server process: {self.server_process.pid}")

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


def get_poetry_dependencies(
    session: nox.Session, only: str = "", *, all_deps: bool = False
) -> Path:
    """Create and return path to a requirements file from poetry.

    This assumes poetry is installed in the session.

    Arguments
    ---------
    session : nox.sessions.Session
        The nox session object.

    only : str, list, optional
        If provided, only return the dependencies that match the provided
        string or strings.

    all : bool, optional, kw-only
        If True, return all dependencies. Default is False. If True, the
        ``only`` argument is ignored.

    Returns
    -------
    Path
        The path to the requirements file.

    Notes
    -----
    This command will not work if the warning about the Poetry export plugin is
    not supressed. Due to an issue with the poetry export command,
    """
    temp_dir = Path(session.create_tmp())
    req_file_path = temp_dir / "requirements.txt"
    only = only if only else "main,test"

    command = [
        "poetry",
        "export",
        f"--only={only}",
        "--without-hashes",
        "--format=requirements.txt",
        f"--output={req_file_path}",
    ]

    if all_deps:
        with Path("pyproject.toml").open("rb") as infile:
            toml_contents = tomllib.load(infile)

        groups = list(toml_contents["tool"]["poetry"]["group"].keys())

        command[2] = f"--with={','.join(groups)}"

    session.run(
        *command,
        external=True,
        silent=True,
    )

    log_message = f"Poetry dependencies written to {req_file_path}"

    with req_file_path.open("r") as file:
        file_contents = "\n".join(
            f"   {line.strip()}" for line in file.readlines()
        )
        session.log(f"{log_message}\n{file_contents}")

    return req_file_path


def install_test_dependencies(
    session: nox.Session,
    packages: list[str] | None = None,
    poetry_groups: list[str] | None = None,
    *,
    conda_install: bool = False,
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

    conda_install : bool, optional, kw-only
        If True, install the dependencies using conda. Otherwise
        use pip. Default is False.
    """
    # If using venv, upgrade pip first. If in a conda env, this is not needed
    # because of nuances with the installed versions.
    if session.venv_backend == "venv" and not conda_install:
        session.install("--upgrade", "pip")

        # Report the pip version
        session.run("python", "-m", "pip", "--version")

    # Get the dependencies from the poetry.lock file if no packages are
    # provided.
    if not packages:
        groups = poetry_groups if poetry_groups else ["main", "test"]
        req_file_path = get_poetry_dependencies(session, ",".join(groups))

    else:
        req_file_path = Path(session.create_tmp()) / "requirements.txt"
        req_file_path.write_text("\n".join(packages))

    if not conda_install:
        session.install("-r", str(req_file_path))

    else:
        session.conda_install("--file", str(req_file_path))


def apply_macos_config(session: nox.Session) -> None:
    """Apply macOS specific configurations."""
    # This configuration is to ensure that conda uses the correct architecture
    # (x86_64) on M-series Macs.
    if sys.platform == "darwin":
        session.env["CONDA_SUBDIR"] = "osx-64"
        session.run("conda", "config", "--env", "--set", "subdir", "osx-64")

        session.log("Setting CONDA_SUBDIR to osx-64.")


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

    session.run(
        "pytest",
        *SessionVariables.dragons_pytest_options,
        *pos_args,
    )


@nox.session(venv_backend="conda", python="3.10", tags=["dragons"])
def dragons_dev_tests(session: nox.Session) -> None:
    """Run the tests for the DRAGONS conda package."""
    apply_macos_config(session)

    # Fetch test dependencies from the poetry.lock file.
    install_test_dependencies(session)
    install_test_dependencies(
        session,
        packages=SessionVariables.dragons_dev_packages,
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
            session.log("DRAGONS repository already exists. Skipping clone.")

        with session.cd("dragons"):
            # Install the DRAGONS package
            session.install("-e", ".")

    # Need to downgrade numpy because of DRAGONS issue 464
    # https://github.com/GeminiDRSoftware/DRAGONS/issues/464
    session.conda_install("numpy<2")

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
    session.install("-e", ".", "--no-deps")

    # Positional arguments after -- are passed to pytest.
    pos_args = session.posargs

    # Run the tests. Need to pass arguments to pytest.
    session.run("pytest", *SessionVariables.unit_pytest_options, *pos_args)


@nox.session(venv_backend="conda", python=SessionVariables.python_versions)
def conda_unit_tests(session: nox.Session) -> None:
    """Run the unit tests."""
    # Configure session channels.
    session.run(
        "conda",
        "config",
        "--env",
        "--add",
        "channels",
        "conda-forge",
    )
    install_test_dependencies(session, conda_install=True)
    session.conda_install(".")

    # Positional arguments after -- are passed to pytest.
    pos_args = session.posargs

    # Run the tests. Need to pass arguments to pytest.
    session.run("pytest", *SessionVariables.unit_pytest_options, *pos_args)


def unit_test_build(session: nox.Session) -> None:
    """Run the unit tests using the build version of the package.

    This is meant to be called from the `build_tests` session.
    """
    # Install the package from the devpi server
    install_test_dependencies(session, poetry_groups=["test"])

    # Install the package from the devpi server
    session.install(
        "astrodata",
    )

    # Positional arguments after -- are passed to pytest.
    pos_args = session.posargs

    # Run the tests. Need to pass arguments to pytest.
    session.run("pytest", *SessionVariables.unit_pytest_options, *pos_args)


def integration_test_build(session: nox.Session) -> None:
    """Run the integration tests using the build version of the package.

    This is meant to be called from the `build_tests` session.
    """
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

    session.install("astrodata")

    # Positional arguments after -- are passed to pytest.
    pos_args = session.posargs

    session.run(
        "pytest",
        *SessionVariables.dragons_pytest_options,
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


@nox.session
def docs(session: nox.Session) -> None:
    """Build the documentation."""
    # Install the documentation dependencies.
    install_test_dependencies(session, poetry_groups=["main", "docs"])

    session.install("-e", ".", "--no-deps")

    # Build the documentation.
    # TODO(teald): Add nitpicky flag to fix warnings. -- Issue #42
    target = Path("_build").absolute()
    session.run("rm", "-rf", target, external=True)
    session.run("sphinx-build", "-W", "docs", target)
    session.log(f"You can find the documentation at: {str(target)}")

    index_loc = target / "index.html"

    session.log(
        f"Your index can be opened in a browser with:\n"
        f"{index_loc.absolute().as_uri()}"
    )


def use_devpi_server(func):
    """Start and stop a devpi server for the session.

    This is used as a function decorator, and must come after the
    ``@nox.session`` decorator.
    """

    @functools.wraps(func)
    def wrapper(session, *args, **kwargs):
        # Create a temporary directory for the devpi server
        with DevpiServerManager(session):
            func(session, *args, **kwargs)

    return wrapper


def build_and_publish_to_devpi(session: nox.Session):
    """Build the astrodata package and publish it.

    If the devpi server is not running, this will raise an error.
    """
    # Build the package and upload it to the devpi server
    tmp_build_dir = Path(session.create_tmp()) / "build"
    tmp_build_dir.mkdir()

    session.run(
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


@nox.session(python=SessionVariables.python_versions, tags=["build_tests"])
@use_devpi_server
def build_tests_unit(session: nox.Session) -> None:
    """Build tests using the devpi server.

    This session will build the package, upload it to an isolated devpi server,
    and run the tests using the build version of the package.
    """
    build_and_publish_to_devpi(session)

    working_dir = Path(session.create_tmp())

    with session.chdir(working_dir):
        unit_test_build(session)


@nox.session(venv_backend="conda", python="3.10", tags=["build_tests"])
@use_devpi_server
def build_tests_integration(session):
    """Build tests using the devpi server.

    This session will build the package, upload it to an isolated devpi server,
    and run the tests using the build version of the package.
    """
    build_and_publish_to_devpi(session)

    working_dir = Path(session.create_tmp())

    with session.chdir(working_dir):
        integration_test_build(session)


@nox.session(python=SessionVariables.python_versions)
def script_tests(session: nox.Session) -> None:
    """Run the script tests."""
    install_test_dependencies(session)
    session.install("-e", ".", "--no-deps")

    # Run the tests. Need to pass arguments to pytest.
    session.run("pytest", "tests/script_tests", *session.posargs)


@nox.session(python=SessionVariables.python_versions)
@use_devpi_server
def build_tests_scripts(session: nox.Session) -> None:
    """Run the script tests using the build version of the package."""
    build_and_publish_to_devpi(session)

    working_dir = Path(session.create_tmp())

    with session.chdir(working_dir):
        # Install the package from the devpi server
        install_test_dependencies(session, poetry_groups=["test"])

        # Install the package from the devpi server
        session.install("astrodata")

        # Run the tests. Need to pass arguments to pytest.
        test_dir = Path(__file__).parent / "tests" / "script_tests"
        session.run("pytest", test_dir, *session.posargs)


@nox.session
def linting(session: nox.Session) -> None:
    """Run the linters."""
    # Install the test dependencies.
    install_test_dependencies(session, poetry_groups=["main", "dev"])

    # Run the linters.
    session.run("ruff", "check", ".")


@nox.session
def devshell(session: nox.Session) -> None:
    """Create a venv for development."""
    # Installing poetry within this isolated env to avoid having devs manage
    # installing a plugin...
    session.install("poetry", "poetry-plugin-export")
    session.env["POETRY_PREFER_ACTIVE_PYTHON"] = "true"
    session.env["POETRY_VIRTUALENVS_CREATE"] = "false"

    venv_path = Path(".astrodata_venv/").absolute()
    activate_path = venv_path / "bin" / "activate"

    # Check that poetry is installed
    try:
        session.run("poetry", "--version", silent=True)

    except nox.command.CommandFailed as err:
        message_lines = (
            "Poetry is not installed. Please install poetry before running ",
            "this session.",
            "Installation instructions can be found at ",
            "https://python-poetry.org/docs/#installation.",
        )
        message = "\n".join(message_lines)

        raise RuntimeError(message) from err

    # Remove any existing venv
    if venv_path.exists():
        session.run("rm", "-rf", str(venv_path), external=True)

    # Create the venv
    session.run(
        "python", "-m", "venv", str(venv_path), "--prompt", "astrodata_venv"
    )

    req_file_path = get_poetry_dependencies(session, all_deps=True)
    venv_python_bin = venv_path / "bin" / "python"

    session.run(
        str(venv_python_bin),
        "-m",
        "pip",
        "install",
        "--upgrade",
        "pip",
        external=True,
    )

    session.run(
        str(venv_python_bin),
        "-m",
        "pip",
        "install",
        "--requirement",
        str(req_file_path),
        external=True,
    )

    # Install the package in editable mode
    session.run(
        str(venv_python_bin),
        "-m",
        "pip",
        "install",
        "-e",
        ".",
        "--no-deps",
        external=True,
    )

    session.log("Virtual environment created.")
    session.log("Activate the environment with:")
    session.log(f"  source {activate_path.relative_to(Path.cwd())}")
    session.log("Deactivate the environment with: deactivate")

    session.notify("initialize_pre_commit")


@nox.session(venv_backend="none")
def devconda(session: nox.Session) -> None:
    """Create a new conda environment for development."""
    conda_venv_name = "astrodata"

    conda_envs_var = "CONDA_EXE"
    try:
        conda_loc = Path(os.getenv(conda_envs_var))

    except TypeError as err:
        message = (
            f"Environment variable {conda_envs_var} is not set. "
            f"Is conda installed?"
        )
        raise RuntimeError(message) from err

    conda_envs_loc = conda_loc.parent.parent / "envs"

    session.env["POETRY_PREFER_ACTIVE_PYTHON"] = "true"
    session.env["POETRY_VIRTUALENVS_PATH"] = conda_envs_loc
    session.env["POETRY_VIRTUALENVS_CREATE"] = "false"

    # Check that conda is installed
    try:
        session.run("conda", "--version", silent=True)

    except nox.command.CommandFailed as err:
        message_lines = (
            "Conda is not installed. Please install conda before running ",
            "this session.",
            "Installation instructions can be found at ",
            "https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html.",
        )
        message = "\n".join(message_lines)

        raise RuntimeError(message) from err

    # Create the requirements file
    req_file_path = get_poetry_dependencies(session, all_deps=True)

    # Remove any existing venv
    session.run("conda", "env", "remove", "--name", conda_venv_name, "--yes")

    # Create the venv
    vers_info = sys.version_info
    python_version = f"{vers_info.major}.{vers_info.minor}.{vers_info.micro}"

    session.run(
        "conda",
        "create",
        "--name",
        conda_venv_name,
        f"python={python_version}",
        "--channel=conda-forge",
        "--yes",
    )

    session.run("conda", "update", "-n", conda_venv_name, "--all", "--yes")

    conda_python = conda_envs_loc / conda_venv_name / "bin" / "python"
    session.run(str(conda_python), "-m", "pip", "install", "--upgrade", "pip")

    session.run(
        str(conda_python),
        "-m",
        "pip",
        "install",
        "--requirement",
        str(req_file_path),
    )

    # Install the package in editable mode
    session.run(
        str(conda_python),
        "-m",
        "pip",
        "install",
        "-e",
        ".",
        "--no-deps",
    )

    session.log("Conda environment created.")
    session.log("Activate the environment with:")
    session.log(f"  conda activate {conda_venv_name}")
    session.log("Deactivate the environment with: conda deactivate")

    session.notify("initialize_pre_commit")


@nox.session(python="3.12")
def initialize_pre_commit(session: nox.Session) -> None:
    """Initialize pre-commit hooks."""
    session.install("pre-commit")
    session.run(
        "pre-commit",
        "install",
        "--install-hooks",
        "--hook-type=pre-commit",
        "--hook-type=commit-msg",
    )


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
    session.run(
        "pytest",
        "tests/integration/dragons/test_calibration_setup.py",
        *pos_args,
        env={"DRAGONSRC": str(dragonsrc_path)},
    )

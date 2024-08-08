======================
Developer Installation
======================

This guide will walk you through setting up a development environment for
|astrodata|. If you are a user looking to install |astrodata| for personal use,
either as a developer or as a user, and are just looking to install the package
as a dependency, see the |Quickstart|.


Developer Documentation Overview
================================

This page specifically helps with setting up a development environment and
running the unit tests.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   testing

Developer environment setup
===========================

This guide will walk you through setting up a development environment for
|astrodata|. If you are a user looking to install |astrodata| for personal use,
and are just looking to install the package as a dependency, see the
|Quickstart|.

.. note::
    This guide assumes you are familiar with the basics of Python development,
    including virtual environments, package management, and testing. It focuses
    on setting up your development environment, not why or how these things
    work.

.. warning::
    This guide only applies to development on UNIX-like systems, like linux
    distributions and macOS. If you're developing on Windows, you may need to
    adapt some of the commands and instructions to work with your system.

Requirements
------------

.. _Poetry: https://python-poetry.org/docs/

To install |astrodata|, you will need the following:

- Python 3.10, 3.11, or 3.12
- Poetry_ in some flavor

Please see the Poetry_ documentation for installation instructions. Note that
it is *not recommended to install Poetry with pip, especially in your working
directory for the project*.  There are several solutions to this in their
documentation.

Instructions
------------

Clone the repository
====================

First, clone the repository from GitHub. Using the command line:

.. code-block:: bash

   git clone git@github.com:GeminiDRSoftware/astrodata.git

Or use your preferred method for cloning a repository.

Install the dependencies
========================

``cd`` into the repository directory:

.. code-block:: bash

   cd astrodata

If you are not already inside a virtual environment of some flavor, such as a
``conda`` or ``venv`` environment, create one now. For example, to create a new
virtual environment with ``venv``:

.. code-block:: bash

   python -m venv .venv
   source .venv/bin/activate

To install the dependencies, navigate to the root of the repository and run:

.. code-block:: bash

   poetry install


This will install all the dependencies needed to run |astrodata| within your
virtual environment, including all test, development, and documentation
dependencies. This installs |astrodata| in a way that's equivalent to
installing with
`pip in editable mode <https://setuptools.pypa.io/en/latest/userguide/development_mode.html>`.

.. note::
    You can install specific dependency groups by running ``poetry install
    --only``. For example, to install the ``main`` and ``test`` dependencies:

    .. code-block:: bash

       poetry install --only main,test

    The groups must be separated by commas, and the groups are defined in the
    ``pyproject.toml`` file.

    Unless you are working on the documentation or testing specifically, you
    will likely never need to isolate dependencies in this way. This is
    primarily used for optimizing CI/CD workflows.

Run the tests
-------------

.. _nox: https://nox.thea.codes/en/stable/

|astrodata| uses nox_ for running tests. To run the tests, simply run:

.. code-block:: bash

   nox

This will run all linting checks and unit tests for any supported Python
distributions it can find, reporting on the coverage at the end of the run.

You can see the available sessions by running:

.. code-block:: bash

   nox -l

This will output information about available session to run. To select a
specific session, use the ``-s`` flag. For example, to run the unit tests on a
Python 3.10 build of |astrodata|:

.. code-block:: bash

   nox -s "build_tests-3.10(unit)""

Or, to run the normal unit tests and not the linter:

.. code-block:: bash

   nox -s "unit"

All tests will be run in isolated environments based on specifications in the
``noxfile.py`` file in the main project directory. Those environments, by
default, are re-created each time you run the tests. To avoid that, you can
pass the ``--reuse-existing-virtualenvs``/``-r`` flag to ``nox``, which will
reuse any existing virtual environments it finds. If the environment isn't
found, it will be made.


Other development commands
--------------------------


Development with a Poetry environment
=====================================

|Poetry| also has a feature to create a shell with the dependencies installed.
This is useful for development, as it allows you to run commands in the
environment without activating it. To create a shell, run:

.. code-block:: bash

   poetry shell

This will create a shell with the dependencies installed. You can then run
commands in this shell as you would in a normal shell. To exit the shell, run:

.. code-block:: bash

   exit

This takes similar steps to the above, but make Poetry handle the environment
for you. While this is convenient, it can be confusing if you're not familiar
with virtual environments and the shell command itself is somewhat limited in
what it can do. It will work quickly, though, and can be useful for quick
development tasks requiring a fresh environment.

Refer to the `Poetry documentation
<https://python-poetry.org/docs/cli/#shell>`__ for more information on the
``shell`` command.

Development without a Virtual Environment
=========================================

If you don't need a virtual environment, you can use the ``poetry run`` command
to run commands in the environment without activating it. For example, to run
the tests without activating the environment, you can run:

.. code-block:: bash

   poetry run tox

This will run the tests in an environment created by poetry without activating
the environment within your shell. This is especially useful for our CI/CD
tasks, and can be useful for running in an environment that is not your
development environment.

Copy/Paste to create and enter a developer environment
------------------------------------------------------

This is for convenience to copy/paste the above commands required to create and
enter a developer shell.

.. code-block:: bash

   # Start in the directory you'd like to keep astrodata in.
   git clone git@github.com:GeminiDRSoftware/astrodata.git
   cd astrodata
   python -m venv .venv
   source .venv/bin/activate
   poetry install

..
   If there is anything else needed for this document, please
   split this up into separate documents. It's at its visual limit here
   (otherwise there's too much text for this to be a quick read).

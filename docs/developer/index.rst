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

   documentation
   testing

.. _dev_environment_setup:

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
``conda`` or ``venv`` environment, you can have ``nox`` create one for you:

.. code-block:: bash

   nox -s devshell  # Creates a virtual environment
   nox -s devconda  # Creates a conda environment

.. note::

   We recommend using the ``devshell`` session, as ``venv`` environments are
   more flexible and allow for more pythonic automation in the development
   process. The ``devconda`` session is provided for users who prefer to use
   conda environments, but it's not as flexible as the ``devshell`` session and
   may require manual tweaking.

.. warning::

   Both of these sessions will create a new environment, either located at
   ``.astrodata_venv`` or in the ``astrodata`` conda environment. It will
   remove any environments found there (for consistency when resetting the
   environment).

Otherwise, to install the dependencies in the current environment--or one
you've set up and activate yourself--navigate to the root of the repository and
run:

.. code-block:: bash

   poetry install


.. _editable_pip: https://setuptools.pypa.io/en/latest/userguide/development_mode.html

This will install all the dependencies needed to run |astrodata| within your
virtual environment, including all test, development, and documentation
dependencies. This installs |astrodata| in a way that's equivalent to
installing with
`pip in editable mode <editable_pip>`.

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

|astrodata| uses |nox| for running tests. To run the tests, simply run:

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

   nox -s "unit_tests"

All tests will be run in isolated environments based on specifications in the
``noxfile.py`` file in the main project directory. Those environments, by
default, are re-created each time you run the tests. To avoid that, you can
pass the ``--reuse-existing-virtualenvs``/``-r`` flag to |nox|, which will
reuse any existing virtual environments it finds. If the environment isn't
found, it will be made.


Other development commands
--------------------------

Development without a Virtual Environment
=========================================

If you don't need a virtual environment, you can use the ``poetry run`` command
to run commands in the environment without activating it. For example, to run
the tests without activating the environment, you can run:

.. code-block:: bash

   poetry run nox

Copy/Paste to create and enter a developer environment
------------------------------------------------------

This is for convenience to copy/paste the above commands required to create and
enter a developer shell.

.. code-block:: bash

   # Start in the directory you'd like to keep astrodata in.
   git clone git@github.com:GeminiDRSoftware/astrodata.git
   cd astrodata
   nox -s devshell
   source .astrodata_venv/bin/activate

..
   If there is anything else needed for this document, please
   split this up into separate documents. It's at its visual limit here
   (otherwise there's too much text for this to be a quick read).

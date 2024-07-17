Developer Installation
======================

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

Please see the |poetry| documentation for installation instructions.

Clone the repository
--------------------

First, clone the repository from GitHub. Using the command line:

.. code-block:: bash

   git clone git@github.com:GeminiDRSoftware/astrodata.git

Or use your preferred method for cloning a repository.

Install the dependencies
------------------------

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

.. _tox: https://tox.readthedocs.io/

|astrodata| uses tox_ for running tests. To run the tests, simply run:

.. code-block:: bash

   tox

If you would like to run a specific test, or using a specific version or
python, you can view the available test environments by running:

.. code-block:: bash

   tox -l

And then run the tests for a specific environment by running:

.. code-block:: bash

   tox -e <environment>
   # e.g., tox -e py310 to run tests with Python 3.10.

.. warning::
    This will be soon replaced by ``nox``, which has continuing support for
    testing with ``conda`` environments. However, the setup/execution is
    similarly simple.

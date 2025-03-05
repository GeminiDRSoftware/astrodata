.. |pytest| replace:: `pytest <https://docs.pytest.org/en/stable/>`__

.. _nox: https://nox.thea.codes/en/stable/
.. _pytest: https://docs.pytest.org/en/stable/

======================
Testing in |astrodata|
======================

.. contents::
    :local:

Core Concepts
=============

Astrodata uses a combination of |pytest|_ and |nox|_ for running tests in
isolated, reproducible environments. |nox|_ is also used for other automation
tasks.

|astrodata| implements different kinds of tests targeting different aspects of
the codebase. These tests are run in isolated environments to ensure that the
tests are reproducible and that the code is tested in a clean environment.

These tests include:

- **Unit tests**: These tests are used to test individual units of code, such as
  functions or classes. They are used to ensure that the code behaves as
  expected when given specific inputs.
- **Integration tests**: These tests are used to test how different parts of the
  codebase interact with each other. They are used to ensure that the code
  behaves as expected when different parts of the codebase are combined.
- **Script tests**: These tests are used to test the scripts in the codebase.
  They are used to ensure that the scripts behave as expected when run. these
  primarily test example scripts within the documentation.
- **Build/Release tests**: These tests are used to test the build and release
  process, and the integrity of the package being released. They are used to
  ensure that the code can be built and released correctly.

There is some cross-pollination between these tests, but they are generally
separated to ensure ease of finding specific tests, and organizing tests to
make understanding and interpretting test results easier.

Running Tests
=============

.. |developer install guide| replace:: :doc:`index`

Running the tests involves some setup. It's assumed you have already installed
and setup |Poetry| as per the |developer install guide|, or are prepared to
work with the |astrodata| source code in some other way.

If you'd like to run the test in your local environment, you can do so by
running the following command from the root of the repository:

.. code-block:: bash

    pytest

This is discouraged, but can be useful for runnin spcific tests or debugging.
To Isolate a test, use a keyword and/or point to a file:

.. code-block:: bash

    pytest -k "test_foo" tests/test_foo.py

The above command will run all tests that match the keyword "test_foo" in their
names in the file ``tests/test_foo.py``.


|nox| is the preferred way to run tests, as it ensures that the tests are run in
clean and isolated environments. Simply run:

.. code-block:: bash

    nox

This will run a subset of the tests recommended for local development, the unit
tests, and their coverage. To see all possible tests, run:

.. code-block:: bash

    nox -l

.. _nox_documentation: https://nox.thea.codes/en/stable/usage.html

This will output information about sessions you can select with ``nox -s``. For
more information about using |nox|, see the `Nox CLI Documentation
<nox_documentation>`_.

.. note::
    |nox| is also used for other automation tasks, such as:
      + building the documentation (``nox -s docs``)
      + linting & formatting (``nox -s linting``)
      + creating development environments (``nox -s devshell``)

Writing Tests
=============

Writing tests is an important part of contributing to |astrodata|. Tests help
ensure that the code behaves as expected, and that changes to the code don't
break existing functionality.

When writing tests, it's important to follow the `testing best practices
<https://docs.pytest.org/en/stable/goodpractices.html>`_ outlined in the
|pytest|_.

Tests are located in the ``tests/`` directory, and are organized by the
type of test they are. For example, unit tests are located in the
``tests/unit/`` directory, integration tests are located in the
``tests/integration/`` directory, and so on.

Unit Tests
----------

Unit tests are used to test individual units of code, such as functions or
classes. They are used to ensure that the code behaves as expected when given
specific inputs. They are also the most common type of test in |astrodata|,
and likely the most common type of test you will write.

Unit tests are in the ``tests/unit`` directory. Testing for specific modules
are collected in individual files. For example, a test for a function in the
``astrodata/utils.py`` module would be located in ``tests/unit/test_utils.py``.

You can run all unit tests (and nothing else) with |nox| by running:

.. code-block:: bash

    nox -s unit

Unit tests require that coverage increases if new code is added. It is highly
encouraged to write tests for contributions before writing new code. If you get
stuck on how to test your idea, feel free to ask for help in the issue or pull
request! Testing is a critical part of the development process, and sometimes
it's trickier than we expect.

Integration Tests
-----------------

Integration tests are used to test how different parts of the codebase interact
with each other in a more hollistic way.

Presently, these test uses |DRAGONS| to test astrodata. This is a work in
progress, and will be updated as the testing framework is updated. |DRAGONS|
just happens to be the most convenient way to run this level of testing at the
moment.

Script Tests
------------

.. warning::
    Script tests are not yet fully implemented. This section is a placeholder
    for future development.

Script tests are used to test the scripts in the codebase. They are used to
ensure that the scripts behave as expected when run. These tests are primarily
used to test example scripts within the documentation.

To run script tests, run:

.. code-block:: bash

    nox -s scripts

This will go through a list of scripts in ``pyproject.toml`` (see the
``[tool.nox.scripts]`` section) and run them. If you add a new script to the
project, you will need to add it to this list to ensure it is tested.

The process for adding a script to be tested is as follows:

#. Add the script to the ``[tool.nox.scripts]`` section of
   ``pyproject.toml``. The key (before the equals sign) should be the path to
   the ``.rst`` file with the example to be run, and the value (after the
   equals sign) should be any arguments to be passed to ``rst_extract``.

    .. code-block:: toml

       [tool.nox.scripts]
       "path/to/script.rst" = "--some-argument"

#. Run ``nox -s scripts -- path/to/script.rst`` to test the script
   individually. Once you're happy with the script, you can run
   ``nox -s scripts`` to test all scripts.

Build/Release Tests
-------------------

.. _devpi_docs: https://devpi.net/docs/devpi/devpi/stable/%2Bd/index.html

Build/release tests test the package being built and sent to, e.g., PyPI. These
tests require a `devpi server <devpi_docs>`_ to be running. This is managed by
classes in ``noxfile.py`` and |nox|, and is something you should be aware of
(though, hopefully, it will not be an issue).

To run all build/release tests, run:

.. code-block:: bash

    nox -t build_tests

This will run all unit tests and integrations tests using the fresh |astrodata|
build.

These tests take a while, and are readily handled by our GitHub Actions
workflows (see ``build_tests.yml``). If you're working on the build/release
process, you may want to run these tests locally, though.

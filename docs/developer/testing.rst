.. |nox| replace:: `nox <https://nox.thea.codes/en/stable/>`__
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
  primarily test example scripts within teh documentation.
- **Build/Release tests**: These tests are used to test the build and release
  process, and the integrity of the package being released. They are used to
  ensure that the code can be built and released correctly.

There is some cross-pollination between these tests, but they are generally
separated to ensure ease of finding specific tests, and organizing tests to
make understanding and interpretting test results easier.

Running Tests
=============

.. |developer install guide| replace:: :doc:`developer/index.rst`

Running the tests involves some setup. It's assumed you have already installed
and setup |Poetry| as per the |developer install guide|, or are prepared to
work with the |astrodata| source code in some other way.

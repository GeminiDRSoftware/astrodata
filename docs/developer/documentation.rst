.. _creating-documentation:

Creating Documentation with Sphinx
==================================

To generate documentation for your project using Sphinx, you can use the ``nox``
task runner and the ``docs`` session.

Prerequisites
-------------

You should have gone through the `Developer environment
setup <dev_environment_setup>`_. This guide assumes you have already installed
the necessary dependencies for the project. If you haven't, and don't want to,
you can just install |poetry| and |nox|.


Generating Documentation
------------------------

To generate documentation for your project, simply run the following command:

.. code-block:: bash

    nox -s docs

This will create the documentation in the ``_build/`` directory in the
top-level project directory.


Customizing Sphinx Configuration
--------------------------------

By default, Sphinx uses a configuration file named `conf.py` located in the
`docs` directory. You can customize the Sphinx configuration by modifying this
file.

For more information on how to configure Sphinx, refer to the Sphinx
`documentation <https://www.sphinx-doc.org/>`_.

Writing Documentation
---------------------

Documentation is written in `reStructuredText (reST)
<https://www.sphinx-doc.org/en/master/usage/restructuredtext/index.html>`_ format.
There are several different forms of documentation in the |astrodata| project:

- `API Reference <api/index>`_: Documentation for the |astrodata| API. Mostly
  auto-generated.
- `Developer Documentation <developer/index>`_: Documentation for developers
  contributing to the |astrodata| project. What you're reading now.
- `User Documentation <user/index>`_: Documentation for users of the
  |astrodata|. This is broken into two parts (historicaly called "manuals"):

    - `User Manual <user/manual>`_: General user documentation for those
      interacting with existing |astrodata| projects and not writing
      |astrodata| code.
    - `Programmer's Manual <user/programmer>`_: Documentation for programmers
      using |astrodata| in their projects. This is more technical than the
      User Manual.

.. note::

    This structure is liable to change. See `Issue #47
    <https://github.com/GeminiDRSoftware/astrodata/issues/47>`_ for updates on
    future documentation plans or to contribute your own ideas.

New contributions to the codebase that add functionality, change existing
functionality, or add new functions/classes should include in-code
documentation in the form of updated or new docstrings.

Documentation should be written in a way that is clear and concise, and should
follow common documentation standards. The current codebase is still being
updated to follow standards, so if you're unsure, feel free to ask for help in
an issue or by contacting an author.

# -*- coding: utf-8 -*-
#
# Configuration file for the Sphinx documentation builder.
#
# This file does only contain a selection of the most common options. For a
# full list see the documentation:
# http://www.sphinx-doc.org/en/master/config

# -- Import sanity check ----------------------------------------------------
# Guard against a stale or duplicate copy of the package being picked up
# from PYTHONPATH (or any other entry on sys.path ahead of the repo itself).
# A stray second copy previously caused a confusing failure deep in
# sphinx.ext.autodoc.importer.get_class_members:
#   TypeError: argument of type 'property' is not iterable
# triggered by sphinx_automodapi's custom `type` attrgetter operating on
# the wrong/stale `Section` class. Fail fast and clearly instead.

import os
import sys

_PACKAGE_NAME = "astrodata"
_EXPECTED_REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")  # adjust if conf.py moves
)


def _check_import_path():
    """Verify the package being documented is loaded from this repo.

    Raises
    ------
    RuntimeError
        If the imported package resolves to a location outside the
        expected repository root, which usually means a stray
        PYTHONPATH entry (or another sys.path entry) is shadowing the
        local checkout with a different copy of the package.
    """
    try:
        module = __import__(_PACKAGE_NAME)
    except ImportError as err:
        raise RuntimeError(
            f"Could not import '{_PACKAGE_NAME}' while building docs. "
            f"Check that it is installed/importable in this environment."
        ) from err

    module_path = os.path.abspath(module.__file__)

    if not module_path.startswith(_EXPECTED_REPO_ROOT):
        pythonpath = os.environ.get("PYTHONPATH", "<not set>")
        raise RuntimeError(
            f"'{_PACKAGE_NAME}' was imported from an unexpected location:\n"
            f"    {module_path}\n"
            f"Expected it to be under:\n"
            f"    {_EXPECTED_REPO_ROOT}\n"
            f"This usually means PYTHONPATH (or another sys.path entry) "
            f"is pointing at a different checkout.\n"
            f"    PYTHONPATH = {pythonpath}\n"
            f"    sys.path   = {sys.path}\n"
            f"Unset PYTHONPATH or remove the offending entry and retry."
        )

_check_import_path()

# --- End of PYTHONPATH check ------------


# The full version, including alpha/beta/rc tags
from astrodata import __version__

release = __version__


# -- Project information -----------------------------------------------------

project = "astrodata"
copyright = "2026, Association of Universities for Research in Astronomy"
author = "DRAGONS Team"

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named "sphinx.ext.*") or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "sphinx.ext.coverage",
    "sphinx.ext.inheritance_diagram",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
    "sphinx.ext.doctest",
    "sphinx.ext.mathjax",
    # "sphinx.ext.autosummary",
    "sphinx_automodapi.automodapi",
    "sphinx_automodapi.smart_resolver",
]

# Run doctest when building the docs
doctest_test_doctest_blocks = "True"
doctest_show_successes = False

# Raise warnings to errors.
warningiserror = True

# Add any paths that contain templates here, relative to this directory.
# templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
source_suffix = ".rst"

# The master toctree document.
master_doc = "index"

# -- Options for intersphinx extension ---------------------------------------

# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {
    "python": ("https://docs.python.org/", None),
    "astropy": ("http://docs.astropy.org/en/stable/", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    # "gemini_instruments": ("https://dragons.readthedocs.io/en/latest/", None),
#    "DRAGONS": ("https://dragons.readthedocs.io/en/stable/", None),
    "DRAGONS": ("https://dragons.readthedocs.io/en/v4.0.0/", None),
}

intersphinx_disabled_reftypes = ["*"]

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = "sphinx_rtd_theme"

# Options for the theme
html_theme_options = {
    "body_max_width": "none",
}

# This logo is not the logo used after rendering; see docs/static and
# specifically docs/static/css/logo_variables.css for more information and the
# actual implementation.
html_logo = "static/logo.svg"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["static"]

html_css_files = [
    "../manuals/_static/color_styles.css",
    "css/logo_variables.css",
]

# Render TODOs; should only be True for the development version.
todo_include_todos = False

# By default, when rendering docstrings for classes, sphinx.ext.autodoc will
# make docs with the class-level docstring and the class-method docstrings,
# but not the __init__ docstring, which often contains the parameters to
# class constructors across the scientific Python ecosystem. The option below
# will append the __init__ docstring to the class-level docstring when rendering
# the docs. For more options, see:
# https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html#confval-autoclass_content
autoclass_content = "both"

# Automodapi options
numpydoc_show_class_members = False


# Add replacement patterns for all the docs
rst_prolog = """
.. |AstroData| replace:: :class:`~astrodata.AstroData`
.. |AstroDataError| replace:: :class:`~astrodata.AstroDataError`
.. |AstroDataMixin| replace:: :class:`~astrodata.AstroDataMixin`
.. |NDAstroData| replace:: :class:`~astrodata.NDAstroData`
.. |Section| replace:: :class:`~astrodata.Section`
.. |TagSet| replace:: :class:`~astrodata.TagSet`
.. |astro_data_descriptor| replace:: :func:`~astrodata.astro_data_descriptor`
.. |astro_data_tag| replace:: :func:`~astrodata.astro_data_tag`
.. |create| replace:: :func:`~astrodata.create`
.. |open| replace:: :func:`~astrodata.from_file`
.. |from_file| replace:: :func:`~astrodata.from_file`
.. |return_list| replace:: :func:`~astrodata.return_list`
.. |version| replace:: :func:`~astrodata.version`
.. |UserGuide| replace:: :doc:`User Guide </manuals/usermanual/index>`
.. |DeveloperGuide| replace:: :doc:`Developer Guide </manuals/progmanual/index>`
.. |ProgrammerGuide| replace:: |DeveloperGuide|
.. |UserManual| replace:: |UserGuide|
.. |ProgManual| replace:: |DeveloperGuide|
.. |ProgrammerManual| replace:: |DeveloperGuide|
.. |QuickStart| replace:: :doc:`Quick Start </quickstart>`
.. |DeveloperInstall| replace:: :doc:`Developer Installation </developer/index>`



.. _`Astropy`: http://docs.astropy.org/en/stable/
.. _`Conda`: https://conda.io/docs/
.. _`Numpy`: https://numpy.org/doc/stable/
.. |numpy| replace:: `Numpy`_
.. |astropy| replace:: `Astropy`_

.. |astrodata| replace:: :mod:`~astrodata`
.. |Mapper| replace:: :class:`~recipe_system.mappers.baseMapper.Mapper`
.. |NDData| replace:: :class:`~astropy.nddata.NDData`
.. |NDArray| replace:: :class:`~numpy.ndarray`
.. |NDWindowing| replace:: :class:`~astropy.nddata.NDWindowing`
.. |NDWindowingAstroData| replace:: :class:`~astrodata.nddata.NDWindowingAstroData`
.. |PrimitiveMapper| replace:: :class:`~recipe_system.mappers.primitiveMapper.PrimitiveMapper`
.. |RecipeMapper| replace:: :class:`~recipe_system.mappers.recipeMapper.RecipeMapper`
.. |Reduce| replace:: :class:`~recipe_system.reduction.coreReduce.Reduce`
.. |Table| replace:: :class:`~astropy.table.Table`
.. |gemini_instruments| replace:: :mod:`DRAGONS:gemini_instruments`
.. |geminidr| replace:: :mod:`DRAGONS:geminidr`
.. |gemini| replace:: `Gemini Observatory <https://www.gemini.edu>`__
.. |mappers| replace:: :mod:`recipe_system.mappers`
.. |recipe_system| replace:: :mod:`recipe_system`
.. |reduce| replace:: ``reduce``
.. |astrodata_descriptor| replace:: :func:`~astrodata.astro_data_descriptor`
.. |factory| replace:: :class:`~astrodata.factory.AstroDataFactory`
.. |AstroDataFactory| replace:: :class:`~astrodata.factory.AstroDataFactory`

.. role:: raw-html(raw)
   :format: html

.. |Poetry| replace:: `Poetry <https://python-poetry.org/>`__
.. |nox| replace:: `nox <https://nox.thea.codes/en/stable/>`__
.. |DRAGONS| replace:: `DRAGONS <https://dragons.readthedocs.io/>`__
.. |RSProgManual| replace:: `Recipe System Programmer Manual <http://dragons-recipe-system-programmers-manual.readthedocs.io/en/{v}/>`__
.. |RSUserManual| replace:: `Recipe System User Manual <http://dragons-recipe-system-users-manual.readthedocs.io/en/{v}/>`__
.. |DRAGONS_install| replace:: `DRAGONS Installation <https://dragons.readthedocs.io/projects/recipe-system-users-manual/en/stable/install.html>`__
.. |DRAGONS_installation| replace:: |DRAGONS_install|

.. |Tags| replace:: :ref:`Tags`
.. |Tag| replace:: :class:`~astrodata.Tag`
.. |Descriptors| replace:: :ref:`ad_descriptors`

.. |IssueTracker| replace:: `Issue Tracker <https://github.com/GeminiDRSoftware/astrodata/issues>`__
.. |astrodata_github| replace:: `astrodata GitHub <https://github.com/GeminiDRSoftware/astrodata>`__

.. TODO: below are broken links

.. |Index| replace:: `Index`

.. |DS9| replace:: `DS9 <https://sites.google.com/cfa.harvard.edu/saoimageds9>`__

.. Definitions for colors, special notes, etc.

.. role:: needs_replacement
"""

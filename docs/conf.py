# -*- coding: utf-8 -*-
#
# Configuration file for the Sphinx documentation builder.
#
# This file does only contain a selection of the most common options. For a
# full list see the documentation:
# http://www.sphinx-doc.org/en/master/config

# The full version, including alpha/beta/rc tags
from astrodata import __version__

release = __version__


# -- Project information -----------------------------------------------------

project = "astrodata"
copyright = "2023, "
author = ""

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
intersphinx_mapping = {"python": ("https://docs.python.org/", None)}

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = "alabaster"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
# html_static_path = ["_static"]

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
.. |open| replace:: :func:`~astrodata.open`
.. |return_list| replace:: :func:`~astrodata.return_list`
.. |version| replace:: :func:`~astrodata.version`
.. |UserGuide| replace:: :doc:`User Guide </manuals/usermanual/index>`
.. |DeveloperGuide| replace:: :doc:`Developer Guide </manuals/progmanual/index>`


.. _`Anaconda`: https://www.anaconda.com/
.. _`Astropy`: http://docs.astropy.org/en/stable/
.. _`Conda`: https://conda.io/docs/
.. _`Numpy`: https://numpy.org/doc/stable/
.. |numpy| replace:: `Numpy`_
.. |astropy| replace:: `Astropy`_

.. |astrodata| replace:: :mod:`~astrodata`
.. |geminidr| replace:: :mod:`~geminidr`
.. |gemini_instruments| replace:: :mod:`gemini_instruments`
.. |gemini| replace:: ``gemini``
.. |Mapper| replace:: :class:`~recipe_system.mappers.baseMapper.Mapper`
.. |mappers| replace:: :mod:`recipe_system.mappers`
.. |NDData| replace:: :class:`~astropy.nddata.NDData`
.. |PrimitiveMapper| replace:: :class:`~recipe_system.mappers.primitiveMapper.PrimitiveMapper`
.. |RecipeMapper| replace:: :class:`~recipe_system.mappers.recipeMapper.RecipeMapper`
.. |recipe_system| replace:: :mod:`recipe_system`
.. |Reduce| replace:: :class:`~recipe_system.reduction.coreReduce.Reduce`
.. |reduce| replace:: ``reduce``
.. |Table| replace:: :class:`~astropy.table.Table`

.. role:: raw-html(raw)
   :format: html

.. |DRAGONS| replace:: :raw-html:`<a href="https://dragons.readthedocs.io/en/{v}/">DRAGONS</a>`
.. |RSProgManual| replace:: :raw-html:`<a href="http://dragons-recipe-system-programmers-manual.readthedocs.io/en/{v}/">Recipe System Programmer Manual</a>`
.. |RSUserManual| replace:: :raw-html:`<a href="http://dragons-recipe-system-users-manual.readthedocs.io/en/{v}/">Recipe System User Manual<a>`

.. |Tags| replace:: :ref:`Tags`
.. |Descriptors| replace:: :ref:`Descriptors`

.. TODO: below are broken links

.. |Index| replace:: `Index`
.. |Examples| replace:: `Examples`

"""

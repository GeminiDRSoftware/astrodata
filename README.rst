.. |DRAGONS| replace:: `DRAGONS`
..  _DRAGONS: https://https://github.com/GeminiDRSoftware/DRAGONS/

.. |astrodatadocs| replace:: `astrodata documentation`
..  _astrodatadocs: https://geminidrsoftware.github.io/astrodata/

.. |astrodatarepo| replace:: `astrodata repository`
.. _astrodatarepo: https://github.com/GeminiDRSoftware/astrodata

``astrodata``
=============

.. image:: https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/teald/d2f3af2a279efc1f6e90d457a3c50e47/raw/covbadge.json
    :alt: A badge displaying the coverage level of this repository.

A package for managing astronomical data through a uniform interface
--------------------------------------------------------------------

``astrodata`` is a package for managing astronomical data through a uniform
interface. It is designed to be used with the
`Astropy <https://www.astropy.org>`_ package. ``astrodata`` was designed by and
for use as part of the |DRAGONS| data reduction pipeline, but it is now
implemented to be useful for any astronomical data reduction or analysis
project.

Unlike managing files using the ``astropy.io.fits`` package alone, ``astrodata``
is designed to be extendible to any data format, and to parse, respond to, and
store metadata in a consistent, intentional way. This makes it especially
useful for managing data from multiple instruments, telescopes, and data
generation utilities.

Installation
------------

``astrodata`` is available on `PyPI <https://pypi.org/project/astrodata>`_ and
can be installed using ``pip``:

.. code-block:: bash

    pip install astrodata

Usage
-----

The most basic usage of ``astrodata`` is to extend the ``astrodata.AstroData``
class, which includes some basic FITS file handling methods by default:

.. code-block:: python

    from astrodata import AstroData

    class MyData(AstroData):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

        def my_method(self):
            print('This is my method, and it tells me about my data.')
            print(self.info())

    data = MyData.read('my_file.fits')
    data.my_method()

This will print out the header of the FITS file, as well as the filename and
path of the file (as it does for ``astropy.io.fits`` objects).

``astrodata`` is designed to be extendible, so you can add your own methods to

Documentation
-------------

Documentation for ``astrodata`` is available at
|astrodatadocs|_. This documentation includes a
user and programmer's guide, as well as a full API reference.


Installing development dependencies
-----------------------------------

``astrodata`` uses `Poetry <https://github.com/python-poetry/poetry>`_ for build
and package management. To install development dependencies, you must clone this
repository. Once you have, at the top level directory of the ``astrodata``
repository run

.. code-block:: terminal

    pip -m install poetry
    poetry install

    # To install without specific development groups
    poetry install --without [test,docs,dev]

License
-------

This project is Copyright (c)  and licensed under
the terms of the Other license. This package is based upon
the `Openastronomy packaging guide <https://github.com/OpenAstronomy/packaging-guide>`_
which is licensed under the BSD 3-clause licence. See the licenses folder for
more information.

Contributing
------------

We love contributions! astrodata is open source,
built on open source, and we'd love to have you hang out in our community.

**Imposter syndrome disclaimer**: We want your help. No, really.

There may be a little voice inside your head that is telling you that you're not
ready to be an open source contributor; that your skills aren't nearly good
enough to contribute. What could you possibly offer a project like this one?

We assure you - the little voice in your head is wrong. If you can write code at
all, you can contribute code to open source. Contributing to open source
projects is a fantastic way to advance one's coding skills. Writing perfect code
isn't the measure of a good developer (that would disqualify all of us!); it's
trying to create something, making mistakes, and learning from those
mistakes. That's how we all improve, and we are happy to help others learn.

Being an open source contributor doesn't just mean writing code, either. You can
help out by writing documentation, tests, or even giving feedback about the
project (and yes - that includes giving feedback about the contribution
process). Some of these contributions may be the most valuable to the project as
a whole, because you're coming to the project with fresh eyes, so you can see
the errors and assumptions that seasoned contributors have glossed over.

Note: This disclaimer was originally written by
`Adrienne Lowe <https://github.com/adriennefriend>`_ for a
`PyCon talk <https://www.youtube.com/watch?v=6Uj746j9Heo>`_, and was adapted by
astrodata based on its use in the README file for the
`MetPy project <https://github.com/Unidata/MetPy>`_.

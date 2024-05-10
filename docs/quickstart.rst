Quickstart
----------

This guide is meant to familiarize you with the most important
concepts of |astrodata|, specifically as someone using |astrodata| to
work with your own data.

If you are a user getting started with |astrodata|, you will likely
wnt to start with the |UserManual|. If you want a more detailed overview
of the library, you can start with the |DeveloperGuide|, which covers the
majority of topics discussed here in more detail.

Installation
============

The easiest way to install |astrodata| is to use `pip`:

.. code-block:: bash

    pip install astrodata

This will install the latest stable release of |astrodata|, as well as
all of its standard dependencies (i.e., not the development dependencies:
see `Advanced Usage`_).

Example Files
=============

As |astrodata| is part of the |DRAGONS| software system, there are some testing
helper functions to download example data for testing purposes. You can
download files using :func:`~astrodata.testing.download_from_archive`:

.. code-block:: python

    from astrodata.testing import download_from_archive

    # Files we'll use in this example.
    files = [
        'N20170614S0201',
        'N20170614S0202',
        'N20170614S0203',
        'N20170614S0204',
        'N20170614S0205',
        'N20170613S0180',
        'N20170613S0181',
        'N20170613S0182',
        'N20170613S0183',
        'N20170613S0184',
        'N20170615S0534',
        'N20170615S0535',
        'N20170615S0536',
        'N20170615S0537',
        'N20170615S0538',
        'N20170702S0178',
        'N20170702S0179',
        'N20170702S0180',
        'N20170702S0181',
        'N20170702S0182',
        'bpm_20170306_gmos-n_Ham_22_full_12amp',
    ]
    files = [f + '.fits' for f in files]

    # Download the files. We'll be placing these in a directory called 'data'.
    for f in files:
        download_from_archive(f, path='data', sub_path='')

These files are from the |DRAGONS| GMOS tutorial, but we'll pretend we don't
have that and want to work with them using |astrodata| alone. They will be
stored in the ``./data/`` directory relative to your current working directory.

Opening Files
=============

The primary way to interact with |astrodata| is through the
:func:`~astrodata.from_file` function. This function will open a file and
create an |AstroData| object from it. You can then use this object to access
the data and metadata in the file.

Let's just open one of the files without any other setup and see what happens:

.. code-block:: python

    import astrodata

    ad = astrodata.from_file('data/N20170614S0201.fits')

    ad.info()

This will print out a summary of the contents of the file. In this case,
it will look something like this:

.. code-block:: text

    Filename: data/N20170614S0201.fits
    Tags:

    Pixels Extensions
    Index  Content                  Type              Dimensions     Format
    [ 0]   science                  NDAstroData       (2112, 288)    uint16
    [ 1]   science                  NDAstroData       (2112, 288)    uint16
    [ 2]   science                  NDAstroData       (2112, 288)    uint16
    [ 3]   science                  NDAstroData       (2112, 288)    uint16
    [ 4]   science                  NDAstroData       (2112, 288)    uint16
    [ 5]   science                  NDAstroData       (2112, 288)    uint16
    [ 6]   science                  NDAstroData       (2112, 288)    uint16
    [ 7]   science                  NDAstroData       (2112, 288)    uint16
    [ 8]   science                  NDAstroData       (2112, 288)    uint16
    [ 9]   science                  NDAstroData       (2112, 288)    uint16
    [10]   science                  NDAstroData       (2112, 288)    uint16
    [11]   science                  NDAstroData       (2112, 288)    uint16

Digesting metadata
==================

Viewing metadata
++++++++++++++++

The |astrodata| library is designed to work with astronomical data, and as such
it has a number of features that are specific to this kind of data. One of the
most important features is digesting and storing FITS-style metadata.

When you open a file with |astrodata|, it will read the metadata from the file
and try to determine the best |AstroData| subclass to use. This is registered
in the |AstroDataFactory| class. Any class you create that inherits from
|AstroData| can be registered with the factory, and |astrodata| will use it
when opening files.

Let's see what the metadata for these files looks like:

.. code-block:: python

    # Iterate over the FITS PHU and print the metadata.
    print(f"PHU Metadata for {ad.filename}:")
    for key, value in ad.phu.items():
        if not any((key, value)):
            continue

        print(f"  {key}: {value}")

which will print out the following (truncated for brevity):

.. code-block:: text

    PHU Metadata for N20170614S0201.fits:
    SIMPLE: True
    BITPIX: 16
    NAXIS: 0
    EXTEND: True
    COMMENT:   FITS (Flexible Image Transport System) format is defined in 'Astronomy
    COMMENT:   and Astrophysics', volume 376, page 359; bibcode: 2001A&A...376..359H
    INSTRUME: GMOS-N
    OBJECT: starfield
    OBSTYPE: OBJECT
    OBSCLASS: science
    <...more header matter...>
    OBSERVER: A. Smith
    OBSERVAT: Gemini-North
    TELESCOP: Gemini-North
    PARALLAX: 0.0
    RADVEL: 0.0
    EPOCH: 2000.0
    EQUINOX: 2000.0
    TRKEQUIN: 2000.0
    SSA: J. Miller
    RA: 285.00429583
    DEC: 24.98093611
    ELEVATIO: 84.5317708333333
    AZIMUTH: -17.5980347222222
    CRPA: 198.346843843749
    HA: +00:07:15.50
    LT: 01:57:59.2

There's quite a bit of metadata here! Let's make a class that gets the most
important parts to us right now to make it easier to work with:

.. code-block:: python

    from astrodata import AstroData, factory
    from astrodata import astro_data_tag, TagSet

    class GMOSAstroData(AstroData):

        # _matches_data is a class attribute that tells the factory to use this
        # class for files that match the given tags.
        @staticmethod
        def _matches_data(source):
            # Your definitions here must return a boolean, with True
            # indicating that the class is appropriate for the file.
            observatory = source[0].header.get('TELESCOP', '').upper()

            return observatory in {'GEMINI-NORTH', 'GEMINI-SOUTH'}


    class GMOSScienceAstroData(GMOSAstroData):

        # _matches_data is a class attribute that tells the factory to use this
        # class for files that match the given tags.
        @staticmethod
        def _matches_data(source):
            obs = source[0].header.get('OBSTYPE', '').upper()
            obstype = source[0].header.get('OBSCLASS', '').upper()

            return obs == 'OBJECT' and obstype == 'SCIENCE'

    # Register the classes with the factory.
    factory.add_class(GMOSAstroData)
    factory.add_class(GMOSScienceAstroData)

Now, when we open a file, |astrodata| will use the appropriate subclass
based on the metadata in the file. Let's see what happens when we open
all the files we downloaded:

.. code-block:: python

    for f in files:
        ad = astrodata.from_file(f'data/{f}')
        print(f"Opened {ad.filename} with class {ad.__class__}")

The result:

.. code-block:: text

    Opened N20170614S0201.fits with class <class '__main__.GMOSScienceAstroData'>
    Opened N20170614S0202.fits with class <class '__main__.GMOSScienceAstroData'>
    Opened N20170614S0203.fits with class <class '__main__.GMOSScienceAstroData'>
    Opened N20170614S0204.fits with class <class '__main__.GMOSScienceAstroData'>
    Opened N20170614S0205.fits with class <class '__main__.GMOSScienceAstroData'>
    Opened N20170613S0180.fits with class <class '__main__.GMOSAstroData'>
    Opened N20170613S0181.fits with class <class '__main__.GMOSAstroData'>
    Opened N20170613S0182.fits with class <class '__main__.GMOSAstroData'>
    Opened N20170613S0183.fits with class <class '__main__.GMOSAstroData'>
    Opened N20170613S0184.fits with class <class '__main__.GMOSAstroData'>
    Opened N20170615S0534.fits with class <class '__main__.GMOSAstroData'>
    Opened N20170615S0535.fits with class <class '__main__.GMOSAstroData'>
    Opened N20170615S0536.fits with class <class '__main__.GMOSAstroData'>
    Opened N20170615S0537.fits with class <class '__main__.GMOSAstroData'>
    Opened N20170615S0538.fits with class <class '__main__.GMOSAstroData'>
    Opened N20170702S0178.fits with class <class '__main__.GMOSAstroData'>
    Opened N20170702S0179.fits with class <class '__main__.GMOSAstroData'>
    Opened N20170702S0180.fits with class <class '__main__.GMOSAstroData'>
    Opened N20170702S0181.fits with class <class '__main__.GMOSAstroData'>
    Opened N20170702S0182.fits with class <class '__main__.GMOSAstroData'>
    Opened bpm_20170306_gmos-n_Ham_22_full_12amp.fits with class <class '__main__.GMOSAstroData'>

The default factory (``factory``, above, where we registered our classes) was
able to determine which files were science files and which were not, and
used the appropriate class to open them.

Accessing Data
==============

Now that we have the data open, we can access the data and metadata in the
file. The data is stored in the ``.data`` attribute of the |AstroData| object,
and the metadata is stored in the ``.phu`` attribute.

Let's see what the data looks like for one of the files:

.. code-block:: python

    # Get the first science extension.
    for ad in (astrodata.from_file(f'data/{f}') for f in files):
        if isinstance(ad, GMOSScienceAstroData):
            break

    print(ad.data[0])
    print(f"{ad.data[0].shape=}")

.. code-block:: text

    [[  0   0   0 ...   0   0   0]
     [  0   0   0 ...   0   0   0]
     [  0   0   0 ...   0   0   0]
     ...
     [361 357 358 ... 366 364 370]
     [367 366 365 ... 359 364 361]
     [375 375 375 ... 351 347 353]]
    ad.data[0].shape=(2112, 288)

This is fine, but what if we're interested in a particular quantity for our
work? It's not much more useful than a FITS file at this point, other than the fancy
class we've created. Let's add a method to our class that will fetch us the
central wavelength in nanometers for the data.

First, we need to remove the ``GMOSScienceAstroData`` class we created from the
factory to avoid conflicts with the new class we're planning:

.. code-block:: python

    factory.remove_class(GMOSScienceAstroData)

Now, let's add a method to a new class, ``GMOSSpectrumScienceAstroData`` class that will fetch the
central wavelength for the data. We'll subclass ``GMOSScienceAstroData`` to
reuse what we've written above.

.. code-block:: python

    from astrodata import astro_data_descriptor

    # Note: This is bad practice! But we're working on an example.
    #       Normally, you will just add this to the old class!
    #       We're only doing this to show how to add a descriptor.
    #       You should *never* inherit from a class in a way that
    #       overwrites the original class.
    class GMOSScienceAstroData(GMOSScienceAstroData):

        @astro_data_descriptor
        def airmass(self):
            # Get the airmass from the header.
            return self.phu.get('AIRMASS')

    # Register the new class with the factory.
    factory.add_class(GMOSScienceAstroData)

Now, when we open a file, we can access the central wavelength like this:

.. code-block:: python

    for f in files:
        ad = astrodata.from_file(f'data/{f}')
        if isinstance(ad, GMOSScienceAstroData):
            print(f"Opened {ad.filename} with class {ad.__class__})")
            print(f"Airmass: {ad.airmass()}")

This is a pretty trivial use case, but one can imagine it being used to
simplify the process of accessing data in a more complex way. These
descriptors can be acessed from subclasses, for example, and you can
get all descriptors from a class using the ``.descriptors`` attribute.

.. code-block:: python

    for f in files:
        ad = astrodata.from_file(f'data/{f}')
        print(f"{ad.filename} descriptors:")
        print(' + ' + ', '.join(ad.descriptors))

You'll see that our ``airmass`` descriptor is available for the
``GMOSScienceAstroData`` class, but not for the ``GMOSAstroData`` class.

Advanced Usage
==============

This is a very basic introduction to |astrodata|, and there are many more
features available. For examples of usage in practice, check out |DRAGONS|'s
|gemini_instruments| package.

If you plan on developing |astrodata|, or you'd like to use the same
development environment |astrodata| uses, you can install |astrodata| from
with development dependencies.

Installing |astrodata| with developer dependencies
++++++++++++++++++++++++++++++++++++++++++++++++++

|astrodata| relies on a number of packages for development, testing, and
documentation. If you want to install these dependencies, you can do so
by installing the code using |Poetry|.

.. code-block:: bash

    git clone https://github.com/GeminiDRSoftware/astrodata
    cd astrodata

    # If you don't have Poetry installed, you can install it with:
    # pip install poetry
    poetry install .

This will install |astrodata| in editable mode, along with all of the
development dependencies. You can now run tests, build documentation,
and run your code using a complete development environment genreated
by |Poetry|:

.. code-block:: bash

    # Run the tests
    # Note: tests are performed on all supported python versions, and if you
    # don't have a specific version installed, that test run will be skipped.
    poetry run tox -rp

    # Build the documentation from source.
    poetry run sphinx-build docs docs/_build

    # Run your code
    poetry run python my_script.py

You may, of course, install these dependencies into a local environment, if you
prefer. For more information about ``Poetry`` and developing with it, see the
`Poetry basic usage documentation
<https://python-poetry.org/docs/basic-usage/#using-your-virtual-environment>`.

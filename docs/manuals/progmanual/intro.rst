.. intro.rst

.. _intro_progmanual:

************
Introduction
************

AstroData is a Python package that provides a common interface to astronomical
data. Originally part of the |DRAGONS| package, the data reduction package
developed at the Gemini Observatory, it has been split into its own package to
allow its use in other projects and to be developed by a wider, public core to
suit the needs of data reduction across the field of astronomy.

AstroData's common interface, the |AstroData| class, is used to abstract the
details of any given data into a set of |Tags|, which can be used to resolve
the properties and reduction requirements of a given data file (most commonly,
a multi-extension FITS file). The |AstroData| class is also used to provide
methods to access the data in a consistent manner, regardless of the
underlying data format.

The |AstroData| class is not intended to be used directly by the user. Instead,
the user should use the :func:`~astrodata.from_file` function, which will return an
|AstroData| object. The :func:`~astrodata.from_file` function will determine the type of
data file being opened and return the appropriate subclass of |AstroData|.

For the programmer using |AstroData| to develop a data reduction pipeline, the
|AstroData| class should be subclassed to provide the functionality required
and to register the new class with the :func:`~astrodata.from_file` function.

Several examples may be found throughout the documentation (see |Examples|). A
simple example is shown below as a complete, executable introduction.

.. code-block:: python

    >>> # Defining an AstroData subclass
    >>> from astrodata import (
    ...     AstroData,
    ...     astro_data_tag,
    ...     astro_data_descriptor,
    ...     TagSet
    ... )
    >>> import astrodata

    >>> class MyAstroData(AstroData):
    ...     @staticmethod
    ...     def _matches_data(source):
    ...         # This method is used by astrodata.from_file to determine if this
    ...         # class should be used to open the data. It should return True
    ...         # if the data is of the correct type, False otherwise.
    ...
    ...         # E.g., if file limited by FITS standard or not for instrument
    ...         # keyword.
    ...         instrument_tags = {'INSTRUME', 'INSTRUMENT'}
    ...
    ...         for tag in instrument_tags:
    ...             if tag in source[0].header:
    ...                 return source[0].header.get(tag).upper() == 'MY_INSTRUMENT'
    ...
    ...         # Could return None by default since it's Falsey, but this is more
    ...         # explicit and follows typing expectations.
    ...         return False
    ...
    ...     @astro_data_tag
    ...     def my_tag(self):
    ...         # This method is used to define a new tag. It should return
    ...         # a string that will be used as the tag name. The method name
    ...         # is used as the tag name by default, but this can be overridden
    ...         # by passing a name to the decorator, e.g.:
    ...         # @astro_data_tag(name='my_tag_name')
    ...         # The method should return None if the tag is not applicable
    ...         # to the data.
    ...
    ...         # This checks that the Primary HDU of the data has a specific
    ...         # keyword, 'MY_TAG'.
    ...         if self.phu.get('MY_TAG') is not None:
    ...             return TagSet(['MY_TAG'])
    ...
    ...         # Not strictly necessary, but here for completeness.
    ...         return TagSet()
    ...
    ...     @astro_data_descriptor
    ...     def my_descriptor(self):
    ...         # This method is used to define a new descriptor. It should
    ...         # return a string that will be used as the descriptor name.
    ...         # The method name is used as the descriptor name by default,
    ...         # but this can be overridden by passing a name to the decorator,
    ...         # e.g.:
    ...         # @astro_data_descriptor(name='my_descriptor_name')
    ...         # The method should return None if the descriptor is not
    ...         # applicable to the data.
    ...
    ...         # Returns None if 'MY_DESC' is not in the Primary HDU
    ...         return self.phu.get('MY_DESC')

    >>> # Registering the new class with astrodata.factory
    >>> astrodata.factory.add_class(MyAstroData)

    >>> # Now, if we give it a file that has the MY_TAG keyword in the Primary HDU,
    >>> # we can open it with astrodata.from_file and it will return an instance of
    >>> # MyAstroData.
    >>> # Defining an example FITS file
    >>> from astropy.io import fits
    >>> import gwcs
    >>> import tempfile

    >>> # Create a new FITS HDU
    >>> phdu = fits.PrimaryHDU(data=[[1, 2], [3, 4]])

    >>> # Add the necessary tags to the FITS header
    >>> phdu.header['INSTRUME'] = 'MY_INSTRUMENT'
    >>> phdu.header['MY_TAG'] = 'example_tag'
    >>> phdu.header['MY_DESC'] = 'example_descriptor'

    >>> # Add a single dummy extension
    >>> image = fits.ImageHDU(data=[[1, 2], [3, 4]])
    >>> hdu = fits.HDUList([phdu, image])

    >>> # Save the FITS file
    >>> with tempfile.NamedTemporaryFile(suffix='.fits') as f:
    ...     hdu.writeto(f, overwrite=True)
    ...
    ...     # Open the file with astrodata.from_file
    ...     ad = astrodata.from_file(f.name)
    ...
    ...     # Check that the tag and descriptor are present
    ...     assert 'MY_TAG' in ad.tags, f"Tag 'my_tag' not found in {ad.tags}"
    ...
    ...     # Check that the tag and descriptor values are correct
    ...     assert ad.my_descriptor() == 'example_descriptor', (
    ...         f"Descriptor 'my_descriptor' has incorrect value: "
    ...         f"{ad.my_descriptor()}"
    ...     )
    ...
    ...     # Finally, make sure that the object is an instance of MyAstroData.
    ...     # We can generally infer this from the above, but it's good to be
    ...     # thorough in our tests (in case any strange API change nullifies
    ...     # the above checks).
    ...     assert isinstance(ad, MyAstroData), (
    ...         f"Incorrect class {type(ad)}, expected MyAstroData"
    ...     )

    >>> # Now that our data is loaded in, we can use the AstroData API to access
    >>> # the data.
    >>> # For example, we can get the data as a numpy array
    >>> data = ad[0].data

    >>> # Or we can get the WCS
    >>> wcs = ad[0].wcs

    >>> # Or we can get the value of a keyword
    >>> my_keyword = ad[0].hdr.get('MY_KEYWORD')

    >>> # Or we can get the resolved tags
    >>> my_tags = ad.tags

    >>> # Or we can get the value of a descriptor
    >>> my_descriptor = ad.my_descriptor()

..
    TODO: Need to move this to a "history" section or something. It's not the
    first thing that should be read by a programmer.

    *************************
    Precedents and Motivation
    *************************


    The Gemini Observatory has produced a number of tools for data processing.
    Historically this has translated into a number of IRAF\ [#IRAF]_ packages but
    the lack of long-term support for IRAF, coupled with the well-known
    difficulty in creating robust reduction pipelines within the IRAF
    environment, led to a decision
    to adopt Python as a programming tool and a new
    package was born: Gemini Python. Gemini Python provided tools to load and
    manipulate Gemini-produced multi-extension FITS\ [#FITS]_ (MEF) files,
    along with a pipeline that
    allowed the construction of reduction recipes. At the center of this package
    was the AstroData subpackage, which supported the abstraction of the FITS
    files.

    Gemini Python reached version 1.0.1, released during November 2014. In 2015
    the Science User Support Department (SUSD) was created at Gemini, which took on the
    responsibility of maintaining the software reduction tools, and started
    planning future steps. With improved oversight and time and thought, it became
    evident that the design of Gemini Python and, specially, of AstroData, made
    further development a daunting task.

    In 2016 a decision was reached to overhaul Gemini Python. While the
    principles behind AstroData were sound, the coding involved unnecessary
    layers of abstraction and eschewed features of the Python language in favor
    of its own implementation. Thus,
    |DRAGONS| was born, with a new, simplified (and backward *incompatible*)
    AstroData v2.0 (which we will refer to simply as AstroData)

    This manual documents both the high level design and some implementation
    details of AstroData, together with an explanation of how to extend the
    package to work for new environments.



    .. rubric:: Footnotes

    .. [#IRAF] http://iraf.net
    .. [#FITS] The `Flexible Image Transport System <https://fits.gsfc.nasa.gov/fits_standard.html>`_
    .. [#DRAGONS] The `Data Reduction for Astronomy from Gemini Observatory North and South <https://github.com/GeminiDRSoftware/DRAGONS>`_ package

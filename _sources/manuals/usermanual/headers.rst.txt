.. headers.rst

.. _headers:

********************
Metadata and Headers
********************

Metadata is a critical component of astronomical observations. These data are
used to clarify and define various aspects of the observation, such as the
instrument configuration, the observation conditions, and the data reduction
history.  The metadata is often stored in the FITS headers of the data files,
and in |AstroData| metadata is manipulated and access in two ways: through
descriptors (via |astro_data_descriptor|) and directly in filetype-specific
header access.

.. warning::
    While we say that header access is filetype-specific, it's important to
    note that this is not the same as saying that the headers are different
    for each file type. The way headers are managed is FITS-centric, and
    therefore implementing header access for a new type requires either updating
    the methods that access headers or converting the headers to use
    :mod:`astropy.io.fits` objects after loading.

    For more information about developing with descriptors, see
    :doc:`../progmanual/descriptors`.

..
    **Try it yourself**

    Download the data package (:ref:`datapkg`) if you wish to follow along and run the
    examples.  Then ::

        $ cd <path>/ad_usermanual/playground
        $ python

    You need to import Astrodata and the Gemini instrument configuration package.

    ::

        >>> import astrodata
        >>> import gemini_instruments

Astrodata Descriptors
=====================

Descriptors provide a mapping between metadata or data and a value or set of
values.  They are a way to access metadata in a consistent way, regardless of
other differences between metadata (such as differences in the instrument,
image type, etc.). Descriptors are implemented as methods, and can be
found using the :meth:`astrodata.AstroData.descriptors` property.

As a user, your interactions with descriptors will depend on the specific
implementation of |AstroData| you are using. For example, if you're using
|gemini_instruments| (from |DRAGONS|), you will have access to the descriptors
defined for Gemini instruments. If you're using |astrodata| directly, you will
have access to the descriptors defined for the generic |AstroData| class.

Descriptors are a way to access metadata in a consistent way, and may perform
operations to arrive at a given value. Descriptors should not, in best
practice, modify the state of any object; instead, they will return a new value
every time they are used. Therefore, they can be more computationally expensive
than direct header access, but they are far more flexible.

For example, if the user is interested to know the effective filter used for a
Gemini observation, normally one needs to know which specific keyword or set of
keywords to look at for that instrument.  However, once the concept of "filter"
is coded as a Descriptor (which happens in |gemini_instruments|), the user only
needs to call the ``filter_name()`` descriptor to retrieve the information.

This is all completely transparent to the user.  One simply opens the data
file and all the descriptors are ready to be used.

.. testsetup::

    import astrodata
    import gemini_instruments

    from astrodata import astro_data_descriptor

.. code-block:: python

    >>> class MyAstroData(astrodata.AstroData):
    ...     @astro_data_descriptor
    ...     def my_descriptor(self):
    ...         return 42

    >>> ad = MyAstroData()
    >>> ad.my_descriptor()
    42

    # Descriptors can be listed as a tuple through the AstroData.descriptors
    # property
    >>> ad.descriptors
    ('my_descriptor',)

.. note::

    Descriptors must be defined for a given |AstroData|-derived class.
    Descriptors are inherited like normal methods, so if a class inherits from
    another class that has descriptors, the new class will have those
    descriptors as well unless they are explicitly overridden.


Accessing Metadata
==================

Accessing Metadata with Descriptors
-----------------------------------

Whenever possible, descriptors should be used to get information from headers.
This allows for straightforward re-usability of the code as it will propogate
to any datasets with an |AstroData| class.

Here are a few examples using Descriptors

.. todo:: [TESTING]

.. code-block:: python

    >>> ad = astrodata.open(path_to_data)

    >>> #--- print a value
    >>> print('The airmass is : ', ad.airmass())
    The airmass is :  1.089

    >>> #--- use a value to control the flow
    >>> if ad.exposure_time() < 240.:
    ...     print('This is a short exposure.')
    ... else:
    ...     print('This is a long exposure.')
    This is a short exposure.

    >>> #--- multiply all extensions by their respective gain
    >>> for ext, gain in zip(ad, ad.gain()):
    ...     ext *= gain

    >>> #--- do arithmetics
    >>> fwhm_pixel = 3.5
    >>> fwhm_arcsec = fwhm_pixel * ad.pixel_scale()

The return value of a descriptor is determined by the developer who created the
descriptor. It's best practice to return a value of the same---or similar,
e.g., an iterable---type for each type of descriptor. However, this is not
always desirable between different instrument sets. For example, Gemini data
and JWST data may have different ways of describing specific values that are
most useful to observers on their respective telescopes. To avoid confusion,
check the return value of the descriptor explicitly when you are experimenting with
new data:

..
    class TestAstroData(astrodata.AstroData):
        @astro_data_descriptor
        def unknown_descriptor(self):
            return "you know what I am now!"

    class OtherTestAstroData(astrodata.AstroData):
        @astro_data_descriptor
        def unknown_descriptor(self):
            string = (
                "My developer decided it's more useful to return the "
                "words discretely"
            )

            return string.split()

.. code-block:: python

    >>> ad = TestAstroData()
    >>> ad.unknown_descriptor()
    'you know what I am now!'

    >>> type(ad.unknown_descriptor())
    <class 'str'>

    >>> ad = OtherTestAstroData()
    >>> ad.unknown_descriptor()
    ['My', 'developer', 'decided', "it's", 'more', 'useful', 'to', 'return', 'the', 'words', 'discretely']

    >>> type(ad.unknown_descriptor())
    <class 'list'>


Descriptors across multiple extensions
--------------------------------------


The dataset used in this section has 4 extensions.  When the descriptor
value can be different for each extension, the descriptor will return a
Python list.

.. todo:: [TESTING]

.. code-block:: python

    >>> ad.airmass()
    1.089
    >>> ad.gain()
    [2.03, 1.97, 1.96, 2.01]
    >>> ad.filter_name()
    'open1-6&g_G0301'

Some descriptors accept arguments.  For example

.. code-block:: python

    >>> ad.filter_name(pretty=True)
    'g'

Accessing Metadata Directly
---------------------------

Not all header content is mapped to descriptors, nor should it be.  Direct
access is available for header content falling outside the scope of the
descriptors.

One important thing to keep in mind is that the PHU (Primary Header Unit) and
the extension headers are accessed slightly differently.  The attribute
``phu`` needs to be used for the PHU, and ``hdr`` for the extension headers.

.. warning::
    The ``phu`` and ``hdr`` attributes are not available for all |AstroData|
    classes.  They are only available for classes that have been implemented to
    use them. The default |AstroData| class without modification does have
    minimal support for these attributes, but for other file types they will
    need to be implemented by a developer/the instrument team.

Here are some examples of direct header access

.. todo:: [TESTING]

.. code-block:: python

    >>> ad = astrodata.open(path_to_data)

    >>> #--- Get keyword value from the PHU
    >>> ad.phu['AOFOLD']
    'park-pos.'

    >>> #--- Get keyword value from a specific extension
    >>> ad[0].hdr['CRPIX1']
    511.862999160781

    >>> #--- Get keyword value from all the extensions in one call.
    >>> ad.hdr['CRPIX1']
    [511.862999160781, 287.862999160781, -0.137000839218696, -224.137000839219]


Whole Headers
-------------

Entire headers can be retrieved as ``fits`` ``Header`` objects

.. todo:: [TESTING]

.. code-block:: python

    >>> ad = astrodata.open(path_to_data)
    >>> type(ad.phu)
    <class 'astropy.io.fits.header.Header'>
    >>> type(ad[0].hdr)
    <class 'astropy.io.fits.header.Header'>

In interactive mode, it is possible to print the headers on the screen as
follows

.. todo:: [TESTING]

.. code-block:: python

    >>> ad.phu
    SIMPLE  =                    T / file does conform to FITS standard
    BITPIX  =                   16 / number of bits per data pixel
    NAXIS   =                    0 / number of data axes
    ....

    >>> ad[0].hdr
    XTENSION= 'IMAGE   '           / IMAGE extension
    BITPIX  =                   16 / number of bits per data pixel
    NAXIS   =                    2 / number of data axes
    ....



Updating, Adding and Deleting Metadata
======================================

Header cards can be updated, added to, or deleted from the headers.  The PHU
and the extensions headers are again accessed in a mostly identical way
with ``phu`` and ``hdr``, respectively.

.. todo:: [TESTING]

.. code-block:: python

    >>> ad = astrodata.open(path_to_data)

Add and update a keyword, without and with comment

.. code-block:: python

    >>> ad.phu['NEWKEY'] = 50.
    >>> ad.phu['NEWKEY'] = (30., 'Updated PHU keyword')

    >>> ad[0].hdr['NEWKEY'] = 50.
    >>> ad[0].hdr['NEWKEY'] = (30., 'Updated extension keyword')

Delete a keyword

.. code-block:: python

    >>> del ad.phu['NEWKEY']
    >>> del ad[0].hdr['NEWKEY']


.. todo:: This should probably be its own page

.. _world_coordinates:

World Coordinate System attribute
=================================

The ``wcs`` of an extension's ``nddata`` attribute (eg. ``ad[0].nddata.wcs``;
see :ref:`pixel-data`) is stored as an instance of ``astropy.wcs.WCS`` (a
standard FITS WCS object) or ``gwcs.WCS`` (a `"Generalized WCS" or gWCS
<https://gwcs.readthedocs.io>`_ object). This defines a transformation between
array indices and some other co-ordinate system such as "World" co-ordinates
(see `APE 14
<https://github.com/astropy/astropy-APEs/blob/master/APE14.rst>`_). GWCS allows
multiple, almost arbitrary co-ordinate mappings from different calibration
steps (eg. CCD mosaicking, distortion correction & wavelength calibration) to
be combined in a single, reversible transformation chain --- but this
information cannot always be represented as a FITS standard WCS. If a gWCS
object is too complex to be defined by the basic FITS keywords, it gets stored
as a table extension named 'WCS' when the |AstroData| instance is saved to a
file (with the same EXTVER as the corresponding 'SCI' array) and the FITS
header keywords are updated to provide an approximation to the true WCS and an
additional keyword ``FITS-WCS`` is added with the value 'APPROXIMATE'.  The
representation in the table is produced using `ASDF
<https://asdf.readthedocs.io>`_, with one line of text per row. Likewise, when
the file is re-opened, the gWCS object gets recreated in ``wcs`` from the
table. If the transformation defined by the gWCS object can be accurately
described by standard FITS keywords, then no WCS extension is created as the
gWCS object can be created from these keywords when the file is re-opened.

In future, it is intended to improve the quality of the FITS approximation
using the Simple Imaging Polynomial convention
(`SIP <https://fits.gsfc.nasa.gov/registry/sip.html>`_) or
a discrete sampling of the World co-ordinate
values will be stored as part of the FITS WCS, following `Greisen et al. (2006)
<http://adsabs.harvard.edu/abs/2006A%26A...446..747G>`_, S6 (in addition to the
definitive 'WCS' table), allowing standard FITS readers to report accurate
World co-ordinates for each pixel.

.. _defining_descriptors:

Adding Descriptors [Advanced Topic]
===================================

To learn how to add descriptors to |AstroData|, see the |progmanual|.

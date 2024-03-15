.. structure.rst

.. _structure:

********************
The AstroData Object
********************

The |AstroData| object represents the data and metadata of a single file on
disk.  As of this version, |AstroData| has a default implementation supporting
the FITS file format. If you wish to extend |AstroData| to support other file
formats, see :ref:`astrodata`.

The internal structure of the |AstroData| object makes uses of astropy's
:class:`~astropy.nddata.NDData`, :mod:`~astropy.table`, and
:class:`~astropy.io.fits.Header`, the latter simply because it is a convenient
ordered dictionary.

Example location
----------------

The examples in this section can be found here: :ref:`user_structure_examples`.

Walkthrough
-----------

Global vs Extension-specific
============================

At the top level, the |AstroData| structure is divided in two types of
information.  In the first category, there is the information that applies to
the data globally, for example the information that would be stored in a FITS
Primary Header Unit, a table from a catalog that matches the RA and DEC of the
field, etc.  In the second category, there is the information specific to
individual science pixel extensions, for example the gain of the amplifier, the
data themselves, the error on those data, etc.

.. todo:: Turn the below code blocks into an example

The composition and amount of information depends on the contents of the file
itself. This information varies dramatically between observatories, so ensure
that you have characterized your data well. Accessing the contents of an
|AstroData| object is done through the :meth:`~astrodata.AstroData.info`
method.

.. testsetup::

    import os


    example_fits_file = os.path.dirname(__file__)
    example_fits_file = os.path.join(
        example_fits_file,
        "../../examples/data/example_mef_file.fits"
    )

.. code::python

    >>> import astrodata

    # You can find the example file in the examples/data directory.
    >>> ad = astrodata.from_file(example_fits_file)
    >>> ad.info()

    Filename: example_mef_file.fits
    Tags: MY_TAG1 MY_TAG2 MY_TAG3

    Pixels Extensions
    Index  Content                  Type              Dimensions     Format
    [ 0]   science                  NDAstroData       (2112, 256)    float32
            .variance             ndarray           (2112, 256)    float32
    [ 1]   science                  NDAstroData       (2112, 256)    float32
            .variance             ndarray           (2112, 256)    float32
    [ 2]   science                  NDAstroData       (2112, 256)    float32
            .variance             ndarray           (2112, 256)    float32
    [ 3]   science                  NDAstroData       (2112, 256)    float32
            .variance             ndarray           (2112, 256)    float32

    Other Extensions
                Type        Dimensions
    .REFERENCE  Table      (245, 16)

..
    Let us look at an example.  The :meth:`~astrodata.AstroData.info` method shows
    the content of the |AstroData| object and its organization, from the user's
    perspective.::

        >>> import astrodata
        >>> import gemini_instruments

        >>> ad = astrodata.open('../playdata/N20170609S0154_varAdded.fits')
        >>> ad.info()
        Filename: N20170609S0154_varAdded.fits
        Tags: ACQUISITION GEMINI GMOS IMAGE NORTH OVERSCAN_SUBTRACTED OVERSCAN_TRIMMED
            PREPARED SIDEREAL

        Pixels Extensions
        Index  Content                  Type              Dimensions     Format
        [ 0]   science                  NDAstroData       (2112, 256)    float32
                .variance             ndarray           (2112, 256)    float32
                .mask                 ndarray           (2112, 256)    uint16
                .OBJCAT               Table             (6, 43)        n/a
                .OBJMASK              ndarray           (2112, 256)    uint8
        [ 1]   science                  NDAstroData       (2112, 256)    float32
                .variance             ndarray           (2112, 256)    float32
                .mask                 ndarray           (2112, 256)    uint16
                .OBJCAT               Table             (8, 43)        n/a
                .OBJMASK              ndarray           (2112, 256)    uint8
        [ 2]   science                  NDAstroData       (2112, 256)    float32
                .variance             ndarray           (2112, 256)    float32
                .mask                 ndarray           (2112, 256)    uint16
                .OBJCAT               Table             (7, 43)        n/a
                .OBJMASK              ndarray           (2112, 256)    uint8
        [ 3]   science                  NDAstroData       (2112, 256)    float32
                .variance             ndarray           (2112, 256)    float32
                .mask                 ndarray           (2112, 256)    uint16
                .OBJCAT               Table             (5, 43)        n/a
                .OBJMASK              ndarray           (2112, 256)    uint8

        Other Extensions
                    Type        Dimensions
        .REFCAT        Table       (245, 16)


The "Pixel Extensions" contain the pixel data (in this case, something specific
to our data type).  Each extension is represented individually in a list
(0-indexed like all Python lists).  The science pixel data, its associated
metadata (extension header), and any other pixel or table extensions directly
associated with that science pixel data are stored in a |NDAstroData| object
which subclasses astropy's |NDData|. An |AstroData| extension is accessed like
any list: ``ad[0]`` will return the first image. To access the science pixels,
one uses ``ad[0].data``; for the object mask of the first extension,
``ad[0].OBJMASK``; etc.

.. todo:: incorporate this into the example
    In the example above, the "Other Extensions" at the bottom of the
    :meth:`~astrodata.AstroData.info` display contains a ``REFCAT`` table which in
    this case is a list of stars from a catalog that overlaps the field of view
    covered by the pixel data. The "Other Extensions" are global extensions. They
    are not attached to any pixel extension in particular. To access a global
    extension one simply uses the name of that extension: ``ad.REFCAT``.


Organization of Global Information
==================================

All the global information can be accessed as attributes of the |AstroData|
object.  The global headers, or Primary Header Unit (PHU), is stored in the
``phu`` attribute as an :class:`astropy.io.fits.Header`.

.. todo:: Put in a link to a good gemini example below where it says
    GEMINI_EXAMPLE

Any global tables are stored in the private attribute ``_tables``. For example,
if we had a ``REFCAT`` global table as part of our data (see example
:needs_replacement:`GEMINI_EXAMPLE` a Python dictionary with the name (eg.
"REFCAT") as the key.  All tables are stored as :class:`astropy.table.Table`.
Access to those table is done using the key directly as if it were a normal
attribute, eg.  ``ad.REFCAT``. Header information for the table, if read in
from a FITS table, is stored in the ``meta`` attribute of the
:class:`astropy.table.Table`, eg.  ``ad.REFCAT.meta['header']``. It is for
information only, it is not used.


Organization of the Extension-specific Information
==================================================

The pixel data are stored in the |AstroData| attribute ``nddata`` as a list
of |NDAstroData| object. The |NDAstroData| object is a subclass of astropy
|NDData| and it is fully compatible with any function expecting an |NDData| as
input.  The pixel extensions are accessible through slicing, eg. ``ad[0]`` or
even ``ad[0:2]``. A slice of an AstroData object is an AstroData object, and
all the global attributes are kept. For example::

    >>> ad[0].info()
    Filename: N20170609S0154_varAdded.fits
    Tags: ACQUISITION GEMINI GMOS IMAGE NORTH OVERSCAN_SUBTRACTED OVERSCAN_TRIMMED
        PREPARED SIDEREAL

    Pixels Extensions
    Index  Content                  Type              Dimensions     Format
    [ 0]   science                  NDAstroData       (2112, 256)    float32
              .variance             ndarray           (2112, 256)    float32
              .mask                 ndarray           (2112, 256)    uint16
              .OBJCAT               Table             (6, 43)        n/a
              .OBJMASK              ndarray           (2112, 256)    uint8

    Other Extensions
                   Type        Dimensions
    .REFCAT        Table       (245, 16)

Note how ``REFCAT`` is still present.

The science data is accessed as ``ad[0].data``, the variance as ``ad[0].variance``,
and the data quality plane as ``ad[0].mask``.   Those familiar with astropy
|NDData| will recognize the structure "data, error, mask", and will notice
some differences. First |AstroData| uses the variance for the error plane, not
the standard deviation. Another difference will be evident only when one looks
at the content of the mask. |NDData| masks contain booleans, |AstroData| masks
are ``uint16`` bit mask that contains information about the type of bad pixels
rather than just flagging them a bad or not. Since ``0`` is equivalent to
``False`` (good pixel), the |AstroData| mask is fully compatible with the
|NDData| mask.

Header information for the extension is stored in the |NDAstroData| ``meta``
attribute.  All table and pixel extensions directly associated with the
science extension are also stored in the ``meta`` attribute.

Technically, an extension header is located in ``ad.nddata[0].meta['header']``.
However, for obviously needed convenience, the normal way to access that header
is ``ad[0].hdr``.

Tables and pixel arrays associated with a science extension are
stored in ``ad.nddata[0].meta['other']`` as a dictionary keyed on the array
name, eg. ``OBJCAT``, ``OBJMASK``.   As it is for global tables, astropy tables
are used for extension tables.  The extension tables and extra pixel arrays are
accessed, like the global tables, by using the table name rather than the long
format, for example ``ad[0].OBJCAT`` and ``ad[0].OBJMASK``.

When reading a FITS Table, the header information is stored in the
``meta['header']`` of the table, eg. ``ad[0].OBJCAT.meta['header']``.  That
information is not used, it is simply a place to store what was read from disk.

The header of a pixel extension directly associated with the science extension
should match that of the science extension.  Therefore such headers are not
stored in |AstroData|. For example, the header of ``ad[0].OBJMASK`` is the
same as that of the science, ``ad[0].hdr``.

The world coordinate system (WCS) is stored internally in the ``wcs`` attribute
of the |NDAstroData| object. It is constructed from the header keywords when
the FITS file is read from disk, or directly from the ``WCS`` extension if
present (see :ref:`the next chapter <fitskeys>`). If the WCS is modified (for
example, by refining the pointing or attaching a more accurate wavelength
calibration), the FITS header keywords are not updated and therefore they should
never be used to determine the world coordinates of any pixel. These keywords are
only updated when the object is written to disk as a FITS file.  The WCS is
retrieved as follows: ``ad[0].wcs``.


.. todo:: Need to rephrase or replace the following subsection
    A Note on Memory Usage
    ======================

    When an file is opened, the headers are loaded into memory, but the pixels
    are not. The pixel data are loaded into memory only when they are first
    needed. This is not real "memory mapping", more of a delayed loading. This
    is useful when someone is only interested in the metadata, especially when
    the files are very large.

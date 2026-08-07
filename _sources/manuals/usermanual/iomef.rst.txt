.. todo:: Need to update the examples

.. iomef.rst

.. _iomef:

************************************************************
Input and Output Operations and Extension Manipulation - MEF
************************************************************

|AstroData| is not intended to exclusively support Multi-Extension FITS (MEF)
files. However, given FITS' unflagging popularity as an astronomical data format,
the base |AstroData| object supports FITS and MEF files without any additional
effort by a user or programmer.

.. note::
    For more information about FITS support and extending |AstroData| to
    support other file formats, see :ref:`astrodata`.


..
    In this chapter, we present examples that will help the reader understand how
    to access the information stored in a MEF with the |AstroData| object and
    understand that mapping.

..
    **Try it yourself**

    Download the data package (:ref:`datapkg`) if you wish to follow along and run the
    examples.  Then ::

        $ cd <path>/ad_usermanual/playground
        $ python


Open and access existing dataset
================================

Read in the dataset
-------------------

The file on disk is loaded into the |AstroData| class associated with the
instrument the data is from. This association is done automatically based on
header content.

.. todo:: replace EXAMPLE FILE with the actual example

.. code-block:: python

    >>> import astrodata
    >>> ad = astrodata.open(EXAMPLE_FILE)
    >>> type(ad)
    <class 'gemini_instruments.gmos.adclass.AstroDataGmos'>

``ad`` has loaded in the file's header and parsed the keys present. Header access is done
through the ``.hdr`` attribute.

.. code-block:: python

    >>> ad.hdr['CCDSEC']
    ['[1:512,1:4224]', '[513:1024,1:4224]', '[1025:1536,1:4224]', '[1537:2048,1:4224]']

    With descriptors:
    >>> ad.array_section(pretty=True)
    ['[1:512,1:4224]', '[513:1024,1:4224]', '[1025:1536,1:4224]', '[1537:2048,1:4224]']

The original path and filename are also stored. If you were to write
the |AstroData| object to disk without specifying anything, path and
file name would be set to ``None``.

.. todo:: Update when updating the example

.. code-block:: python

    >>> ad.path
    '../playdata/N20170609S0154.fits'
    >>> ad.filename
    'N20170609S0154.fits'


Accessing the content of a MEF file
-----------------------------------

|AstroData| uses |NDData| as the core of its structure. Each FITS extension
becomes a |NDAstroData| object, subclassed from |NDData|, and is added to
a list representing all extensions in the file.

.. note::
    For details on the |AstroData| object, please refer to
    :ref:`structure`.

Pixel data
^^^^^^^^^^

To access pixel data, the list index and the ``.data`` attribute are used. That
returns a :class:`numpy.ndarray`. The list of |NDAstroData| is zero-indexed.
*Extension number 1 in a MEF is index 0 in an |AstroData| object*.

.. code-block:: python

    >>> ad = astrodata.open('../playdata/N20170609S0154_varAdded.fits')
    >>> data = ad[0].data
    >>> type(data)
    <class 'numpy.ndarray'>
    >>> data.shape
    (2112, 256)

.. note::
    This implementation ignores the fact that the first extension in a MEF
    file is the Primary Header Unit (PHU). The PHU is accessibly through the
    ``.phu`` attribute of the |AstroData| object, and indexing with ``[i]``
    notation will only access the extensions.

.. note::
    Remember that in a :class:`~numpy.ndarray` the 'y-axis' of the image is
    accessed through the first number.

.. todo:: need to review how this implemented and update this. It's pretty
    confusing the way it's worded right now (not something trivial to word
    precisely and comprehensibly, either).

The variance and data quality planes, the ``VAR`` and ``DQ`` planes in Gemini
MEF files, are represented by the ``.variance`` and ``.mask`` attributes,
respectively. They are not their own "extension", they don't have their own
index in the list, unlike in a MEF. They are attached to the pixel data,
packaged together by the |NDAstroData| object. They are represented as
:class:`numpy.ndarray` just like the pixel data

.. code-block:: python

    >>> var = ad[0].variance
    >>> dq = ad[0].mask

Tables
^^^^^^

Tables in the MEF file will also be loaded into the |AstroData| object. If a table
is associated with a specific science extension through the EXTVER header keyword, that
table will be packaged within the same AstroData extension as the pixel data
and accessible like an attribute.  The |AstroData| "extension" is the
|NDAstroData| object plus any table or other pixel array associated with the
image data. If the table is not associated with a specific extension and
applies globally, it will be added to the AstroData object as a global
addition. No indexing will be required to access it.  In the example below, one
``OBJCAT`` is associated with each extension, while the ``REFCAT`` has a global
scope

.. code-block:: python

    >>> ad.info()
    Filename: ../playdata/N20170609S0154_varAdded.fits
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


The tables are stored internally as :class:`astropy.table.Table` objects.

.. code-block:: python

    >>> ad[0].OBJCAT
    <Table length=6>
    NUMBER X_IMAGE Y_IMAGE ... REF_MAG_ERR PROFILE_FWHM PROFILE_EE50
    int32  float32 float32 ...   float32     float32      float32
    ------ ------- ------- ... ----------- ------------ ------------
         1 283.461 55.4393 ...     0.16895       -999.0       -999.0
    ...
    >>> type(ad[0].OBJCAT)
    <class 'astropy.table.table.Table'>

    >>> refcat = ad.REFCAT
    >>> type(refcat)
    <class 'astropy.table.table.Table'>

.. note::
    Tables are accessed through attribute notation. However, if a conflicting
    attribute exists for a given |AstroData| or |NDData| object, a
    :py:exc:`AttributeError` will be raised to avoid confusion.

Headers
^^^^^^^

Headers are stored in the |NDAstroData| ``.meta`` attribute as
:class:`astropy.io.fits.Header` objects, which implements a ``dict``-like
object. Headers associated with extensions are stored with the corresponding
|NDAstroData| object. The MEF Primary Header Unit (PHU) is stored as an
attribute in the |AstroData| object. When slicing an |AstroData| object or
accessing an index, the PHU will be included in the new sliced object.  The
slice of an |AstroData| object is an |AstroData| object.  Headers can be
accessed directly, or for some predefined concepts, the use of Descriptors is
preferred.  More detailed information on Headers is covered in  the section
:ref:`headers`.

Using Descriptors

.. code-block:: python

    >>> ad = astrodata.open('../playdata/N20170609S0154.fits')
    >>> ad.filter_name()
    'open1-6&g_G0301'
    >>> ad.filter_name(pretty=True)
    'g'

Using direct header access

.. code-block:: python

    >>> ad.phu['FILTER1']
    'open1-6'
    >>> ad.phu['FILTER2']
    'g_G0301'

Accessing the extension headers

.. code-block:: python

    >>> ad.hdr['CCDSEC']
    ['[1:512,1:4224]', '[513:1024,1:4224]', '[1025:1536,1:4224]', '[1537:2048,1:4224]']
    >>> ad[0].hdr['CCDSEC']
    '[1:512,1:4224]'

    With descriptors:
    >>> ad.array_section(pretty=True)
    ['[1:512,1:4224]', '[513:1024,1:4224]', '[1025:1536,1:4224]', '[1537:2048,1:4224]']


Modify Existing MEF Files
=========================

Appending an extension
----------------------

Extensions can be appended to an |AstroData| objects using the
:meth:`~astrodata.AstroData.append` method.

Here is an example appending a whole AstroData extension, with pixel data,
variance, mask and tables. While these are treated as separate extensions in
the MEF file, they are all packaged together in the |AstroData| object.

.. code-block:: python

    >>> ad = astrodata.open('../playdata/N20170609S0154.fits')
    >>> advar = astrodata.open('../playdata/N20170609S0154_varAdded.fits')

    >>> ad.info()
    Filename: ../playdata/N20170609S0154.fits
    Tags: ACQUISITION GEMINI GMOS IMAGE NORTH RAW SIDEREAL UNPREPARED
    Pixels Extensions
    Index  Content                  Type              Dimensions     Format
    [ 0]   science                  NDAstroData       (2112, 288)    uint16
    [ 1]   science                  NDAstroData       (2112, 288)    uint16
    [ 2]   science                  NDAstroData       (2112, 288)    uint16
    [ 3]   science                  NDAstroData       (2112, 288)    uint16

    >>> ad.append(advar[3])
    >>> ad.info()
    Filename: ../playdata/N20170609S0154.fits
    Tags: ACQUISITION GEMINI GMOS IMAGE NORTH RAW SIDEREAL UNPREPARED
    Pixels Extensions
    Index  Content                  Type              Dimensions     Format
    [ 0]   science                  NDAstroData       (2112, 288)    uint16
    [ 1]   science                  NDAstroData       (2112, 288)    uint16
    [ 2]   science                  NDAstroData       (2112, 288)    uint16
    [ 3]   science                  NDAstroData       (2112, 288)    uint16
    [ 4]   science                  NDAstroData       (2112, 256)    float32
              .variance             ndarray           (2112, 256)    float32
              .mask                 ndarray           (2112, 256)    int16
              .OBJCAT               Table             (5, 43)        n/a
              .OBJMASK              ndarray           (2112, 256)    uint8

    >>> ad[4].hdr['EXTVER']
    4
    >>> advar[3].hdr['EXTVER']
    4

As you can see above, the fourth extension of ``advar``, along with everything
it contains was appended at the end of the first |AstroData| object. However,
note that, because the ``EXTVER`` of the extension in ``advar`` was 4, there are
now two extensions in ``ad`` with this ``EXTVER``. This is not a problem because
``EXTVER`` is not used by |AstroData| (it uses the index instead) and it is handled
only when the file is written to disk.

In this next example, we are appending only the pixel data, leaving behind the other
associated data. One can attach the headers too, like we do here.

.. code-block:: python

    >>> ad = astrodata.open('../playdata/N20170609S0154.fits')
    >>> advar = astrodata.open('../playdata/N20170609S0154_varAdded.fits')

    >>> ad.append(advar[3].data, header=advar[3].hdr)
    >>> ad.info()
    Filename: ../playdata/N20170609S0154.fits
    Tags: ACQUISITION GEMINI GMOS IMAGE NORTH RAW SIDEREAL UNPREPARED
    Pixels Extensions
    Index  Content                  Type              Dimensions     Format
    [ 0]   science                  NDAstroData       (2112, 288)    uint16
    [ 1]   science                  NDAstroData       (2112, 288)    uint16
    [ 2]   science                  NDAstroData       (2112, 288)    uint16
    [ 3]   science                  NDAstroData       (2112, 288)    uint16
    [ 4]   science                  NDAstroData       (2112, 256)    float32

Notice how a new extension was created but ``variance``, ``mask``, the OBJCAT
table and OBJMASK image were not copied over. Only the science pixel data was
copied over.

Please note, there is no implementation for the "insertion" of an extension.

Removing an extension or part of one
------------------------------------
Removing an extension or a part of an extension is straightforward. The
Python command :func:`del` is used on the item to remove. Below are a few
examples, but first let us load a file

.. code-block:: python

    >>> ad = astrodata.open('../playdata/N20170609S0154_varAdded.fits')
    >>> ad.info()

As you go through these examples, check the new structure with :func:`ad.info()`
after every removal to see how the structure has changed.

Deleting a whole |AstroData| extension, the fourth one

.. code-block:: python

    >>> del ad[3]

Deleting only the variance array from the second extension

.. code-block:: python

    >>> ad[1].variance = None

Deleting a table associated with the first extension

.. code-block:: python

    >>> del ad[0].OBJCAT

Deleting a global table, not attached to a specific extension

.. code-block:: python

    >>> del ad.REFCAT


Writing back to a file
======================

The |AstroData| class implements methods for writing its data back to a
MEF file on disk.

Writing to a new file
---------------------

There are various ways to define the destination for the new FITS file.
The most common and natural way is

.. code-block:: python

    >>> ad.write('new154.fits')
    # If the file already exists, an error will be raised unless overwrite=True
    # is specified.
    >>> ad.write('new154.fits', overwrite=True)

This will write a FITS file named 'new154.fits' in the current directory.  With
``overwrite=True``, it will overwrite the file if it already exists.  A path
can be prepended to the filename if the current directory is not the
destination.

Note that ``ad.filename`` and ``ad.path`` have not changed, we have just
written to the new file, the |AstroData| object is in no way associated with
that new file.

.. code-block:: python

    >>> ad.path
    '../playdata/N20170609S0154.fits'
    >>> ad.filename
    'N20170609S0154.fits'

If you want to create that association, the ``ad.filename`` and ``ad.path``
needs to be modified first.  For example

.. code-block:: python

    >>> ad.filename = 'new154.fits'
    >>> ad.write(overwrite=True)

    >>> ad.path
    '../playdata/new154.fits'
    >>> ad.filename
    'new154.fits'

Changing ``ad.filename`` also changes the filename in the ``ad.path``. The
sequence above will write 'new154.fits' not in the current directory but
rather to the directory that is specified in ``ad.path``.

.. todo:: Need to update the code to change the filename, this seems a little
    sus to me.

    Maybe introduce an "original filename" attribute that is not changed when
    the filename is changed.  That way, the user can always go back to the
    original filename.

    Also, could have a printed note that the filename is changed. E.g., an
    asterisk next to the filename value and a footnote about the meaning there.

    Will need to be in the next version, though, since this is breaking.

.. warning::

    :func:`ad.write` has an argument named ``filename``.  Setting ``filename``
    in the call to :func:`ad.write`, as in ``ad.write(filename='new154.fits')``
    will NOT modify ``ad.filename`` or ``ad.path``.  The two "filenames", one a
    method argument the other a class attribute have no association to each
    other.


Updating an existing file on disk
----------------------------------

Updating an existing file on disk requires explicitly allowing overwrite.

If you have not written 'new154.fits' to disk yet (from previous section)

.. code-block:: python

    >>> ad = astrodata.open('../playdata/N20170609S0154.fits')
    >>> ad.write('new154.fits', overwrite=True)

Now let's open 'new154.fits', and write to it

.. code-block:: python

    >>> adnew = astrodata.open('new154.fits')
    >>> adnew.write(overwrite=True)


A note on FITS header keywords
------------------------------

.. _fitskeys:

When writing an |AstroData| object as a FITS file, it is necessary to add or
update header keywords to represent some of the internally-stored information.
Any extensions that did not originally belong to a given |AstroData| instance
will be assigned new ``EXTVER`` keywords to avoid conflicts with existing
extensions, and the internal ``WCS`` is converted to the appropriate FITS keywords.
Note that in some cases it may not be possible for standard FITS keywords to
accurately represent the true ``WCS``. In such cases, the FITS keywords are written
as an approximation to the true ``WCS``, together with an additional keyword

.. code::python

   FITS-WCS= 'APPROXIMATE'        / FITS WCS is approximate

to indicate this. The accurate ``WCS`` is written as an additional FITS extension with
``EXTNAME='WCS'`` that AstroData will recognize when the file is read back in. The
``WCS`` extension will not be written to disk if there is an accurate FITS
representation of the ``WCS`` (e.g., for a simple image).


Create New MEF Files
====================

A new MEF file can be created from an existing, maybe modified, file or
created from scratch (e.g., using computer-generated data/images).

Create New Copy of MEF Files
----------------------------

Basic example
^^^^^^^^^^^^^

As seen above, a MEF file can be opened with |astrodata|, the |AstroData|
object can be modified (or not), and then written back to disk under a
new name.

.. code-block:: python

    >>> ad = astrodata.open('../playdata/N20170609S0154.fits')
    ... optional modifications here ...
    >>> ad.write('newcopy.fits')


Needing true copies in memory
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Sometimes it is a true copy in memory that is needed.  This is not specific
to MEF.  In Python, doing something like ``adnew = ad`` does not create a
new copy of the AstrodData object; it just gives it a new name.  If you
modify ``adnew`` you will be modifying ``ad`` too.  They point to the same
block of memory.

To create a true independent copy, the ``deepcopy`` utility needs to be used. ::

.. code-block:: python

    >>> from copy import deepcopy
    >>> ad = astrodata.open('../playdata/N20170609S0154.fits')
    >>> adcopy = deepcopy(ad)

.. warning::
    ``deepcopy`` can cause memory problems, depending on the size of the data
    being copied as well as the size of objects it references. If you notice
    your memory becoming large/full, consider breaking down the copy into
    smaller pieces and f.


Create New MEF Files from Scratch
---------------------------------
Before one creates a new MEF file on disk, one has to create the AstroData
object that will be eventually written to disk.  The |AstroData| object
created also needs to know that it will have to be written using the MEF
format. This is fortunately handled fairly transparently by |astrodata|.

The key to associating the FITS data to the |AstroData| object is simply to
create the |AstroData| object from :mod:`astropy.io.fits` header objects. Those
will be recognized by |astrodata| as FITS and the constructor for FITS will be
used. The user does not need to do anything else special. Here is how it is
done.

Create a MEF with basic header and data array set to zeros
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    >>> import numpy as np
    >>> from astropy.io import fits

    >>> phu = fits.PrimaryHDU()

    >>> pixel_data = np.zeros((100,100))

    >>> hdu = fits.ImageHDU()
    >>> hdu.data = pixel_data

    >>> ad = astrodata.create(phu)
    >>> ad.append(hdu, name='SCI')

    # Or another way to do the last two blocks:
    >>> hdu = fits.ImageHDU(data=pixel_data, name='SCI')
    >>> ad = astrodata.create(phu, [hdu])

    # Finally write to a file.
    >>> ad.write('new_MEF.fits')

Associate a pixel array with a science pixel array
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Only main science (labed as ``SCI``) pixel arrays are added an
|AstroData| object.  It not uncommon to have pixel information associated with
those main science pixels, such as pixel masks, variance arrays, or other
information.

These pixel arrays are added to specific slice of the astrodata object they are
associated with.

Building on the |AstroData| object we created in the previously, we can add a
new pixel array directly to the slice(s) of the |AstroData| object it should be
associated with by assigning it as an attribute of the object.

.. code-block:: python

    >>> extra_data = np.ones((100, 100))
    >>> ad[0].EXTRADATA = extra_data

When the file is written to disk as a MEF, an extension will be created with
``EXTNAME = EXTRADATA`` and an ``EXTVER`` that matches the slice's ``EXTVER``,
in this case is would be ``1``.

.. todo:: Need to revisit below after working on tables section

Represent a table as a FITS binary table in an ``AstroData`` object
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

One first needs to create a table, either an :class:`astropy.table.Table`
or a :class:`~astropy.io.fits.BinTableHDU`. See the |astropy| documentation
on tables and this manual's :ref:`section <tables>` dedicated to tables for
more information.

In the first example, we assume that ``my_astropy_table`` is
a :class:`~astropy.table.Table` ready to be attached to an |AstroData|
object.  (Warning: we have not created ``my_astropy_table`` therefore the
example below will not run, though this is how it would be done.)

.. code-block:: python

    >>> phu = fits.PrimaryHDU()
    >>> ad = astrodata.create(phu)

    >>> astrodata.add_header_to_table(my_astropy_table)
    >>> ad.append(my_astropy_table, name='SMAUG')


In the second example, we start with a FITS :class:`~astropy.io.fits.BinTableHDU`
and attach it to a new |AstroData| object. (Again, we have not created
``my_fits_table`` so the example will not run.) ::

    >>> phu = fits.PrimaryHDU()
    >>> ad = astrodata.create(phu)
    >>> ad.append(my_fits_table, name='DROGON')

As before, once the |AstroData| object is constructed, the ``ad.write()``
method can be used to write it to disk as a MEF file.

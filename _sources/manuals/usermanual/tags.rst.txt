.. tags.rst

.. _tags:

***************
Astrodata |Tag|
***************

What is an Astrodata |Tag|?
===========================

|Tag| is a way to describe the data in an |AstroData| object. Tags are used to
idenfity the type of |AstroData| object to be created when |open| is called.

A |Tag| is added to an |AstroData| object by defining a function wrapped with
the :func:`~astrodata.astro_data_tag` decorator.  The function must return a
:class:`~astrodata.TagSet` object, which describes the behavior of a tag.

For example, the following function defines a tag called "RAW"

.. testsetup::

    from astrodata import TagSet, astro_data_tag

.. code-block:: python

    class RawAstroData(AstroData):
        @astro_data_tag
        def _tag_raw(self):
            """Identify if this is raw data"""
            if self.phu.get('PROCTYPE') == 'RAW':
                return TagSet(['RAW'])

Now, if we call |open| on a file that has a PROCTYPE keyword set to "RAW", the
|AstroData| object will have the "`RAW`" tag


.. code-block:: python

    >>> ad = astrodata.open('somefile.fits')
    >>> ad.tags
    {'RAW'}

From here, these tag sets can be used to understand what the data is describing
and how best to process it. It can also contain information about the state of
processing (e.g., ``RAW`` vs ``PROCESSED``), or any important flags.

.. _ad_tags: :ref:`../progmanual/tags.rst`

These tags are meant to work well with FITS data, using the headers to
determine what the data is.  However, they can be used with any data type that
can be described by a set of tags, as long as they are properly defined by the
developer (see ad_tags_ for more information about developing with |Tag|).

..
    The Astrodata Tags identify the data represented in the |AstroData| object.
    When a file on disk is opened with |astrodata|, the headers are inspected to
    identify which specific |AstroData| class needs to be loaded,
    :class:`~gemini_instruments.gmos.AstroDataGmos`,
    :class:`~gemini_instruments.niri.AstroDataNiri`, etc. Based on the class the data is
    associated with, a list of "tags" will be defined. The tags will tell whether the
    file is a flatfield or a dark, if it is a raw dataset, or if it has been processed by the
    recipe system, if it is imaging or spectroscopy. The tags will tell the
    users and the system what that data is and also give some information about
    the processing status.

For some examples of tags in production code, see the |gemini_instruments|
package, which defined a number of |AstroData| derivatives used as part of the
|DRAGONS| data reduction library for reading as well as processing data.

Using the Astrodata Tags
========================

**Try it yourself**

Download the data package (:ref:`datapkg`) if you wish to follow along and run the
examples.  Then ::

    $ cd <path>/ad_usermanual/playground
    $ python

Before doing anything, you need to import |astrodata| and the Gemini instrument
configuration package (|gemini_instruments|).

::

    >>> import astrodata
    >>> import gemini_instruments

Let us open a Gemini dataset and see what tags we get::

    >>> ad = astrodata.open('../playdata/N20170609S0154.fits')
    >>> ad.tags
    {'RAW', 'GMOS', 'GEMINI', 'NORTH', 'SIDEREAL', 'UNPREPARED', 'IMAGE', 'ACQUISITION'}

The file we loaded is raw, GMOS North data. It is a 2D image and it is an
acquisition image, not a science observation. The "UNPREPARED" tag indicates
that the file has never been touched by the Recipe System which runs a
"prepare" primitive as the first step of each recipe.

Let's try another ::

    >>> ad = astrodata.open('../playdata/N20170521S0925_forStack.fits')
    >>> ad.tags
    {'GMOS', 'GEMINI', 'NORTH', 'SIDEREAL', 'OVERSCAN_TRIMMED', 'IMAGE',
    'OVERSCAN_SUBTRACTED', 'PREPARED'}

This file is a science GMOS North image.  It has been processed by the
Recipe System.  The overscan level has been subtracted and the overscan section
has been trimmed away.  The tags do NOT include all the processing steps. Rather,
at least from the time being, it focuses on steps that matter when associating
calibrations.

The tags can be used when coding.  For example

.. code-block:: python

    >>> if 'GMOS' in ad.tags:
    ...    print('I am GMOS')
    ... else:
    ...    print('I am these instead:', ad.tags)

And

.. code-block:: python

    >>> if {'IMAGE', 'GMOS'}.issubset(ad.tags):
    ...   print('I am a GMOS Image.')

.. todo:: Below needs to be ported back to DRAGONS documentation since it is a
    part of gempy (I think, definitely a part of DRAGONS no matter what)

    Using typewalk

    In DRAGONS, there is a convenience tool that will list the Astrodata tags
    for all the FITS file in a directory.

    To try it, from the shell, not Python, go to the "playdata" directory and
    run typewalk

    .. code-block:: console

        % cd <path>/ad_usermanual/playdata
        % typewalk

        directory:  /data/workspace/ad_usermanual/playdata
        N20170521S0925_forStack.fits ...... (GEMINI) (GMOS) (IMAGE) (NORTH) (OVERSCAN_SUBTRACTED) (OVERSCAN_TRIMMED) (PREPARED) (SIDEREAL)
        N20170521S0926_forStack.fits ...... (GEMINI) (GMOS) (IMAGE) (NORTH) (OVERSCAN_SUBTRACTED) (OVERSCAN_TRIMMED) (PREPARED) (PROCESSED) (PROCESSED_SCIENCE) (SIDEREAL)
        N20170609S0154.fits ............... (ACQUISITION) (GEMINI) (GMOS) (IMAGE) (NORTH) (RAW) (SIDEREAL) (UNPREPARED)
        N20170609S0154_varAdded.fits ...... (ACQUISITION) (GEMINI) (GMOS) (IMAGE) (NORTH) (OVERSCAN_SUBTRACTED) (OVERSCAN_TRIMMED) (PREPARED) (SIDEREAL)
        estgsS20080220S0078.fits .......... (GEMINI) (GMOS) (LONGSLIT) (LS) (PREPARED) (PROCESSED) (PROCESSED_SCIENCE) (SIDEREAL) (SOUTH) (SPECT)
        gmosifu_cube.fits ................. (GEMINI) (GMOS) (IFU) (NORTH) (ONESLIT_RED) (PREPARED) (PROCESSED) (PROCESSED_SCIENCE) (SIDEREAL) (SPECT)
        new154.fits ....................... (ACQUISITION) (GEMINI) (GMOS) (IMAGE) (NORTH) (RAW) (SIDEREAL) (UNPREPARED)
        Done DataSpider.typewalk(..)

    ``typewalk`` can be used to select specific data based on tags, and even create
    lists

    .. code-block::console

        % typewalk --tags RAW
        directory:  /data/workspace/ad_usermanual/playdata
        N20170609S0154.fits ............... (ACQUISITION) (GEMINI) (GMOS) (IMAGE) (NORTH) (RAW) (SIDEREAL) (UNPREPARED)
        new154.fits ....................... (ACQUISITION) (GEMINI) (GMOS) (IMAGE) (NORTH) (RAW) (SIDEREAL) (UNPREPARED)
        Done DataSpider.typewalk(..)

    .. code-block::console

        % typewalk --tags RAW -o rawfiles.lis
        % cat rawfiles.lis
        # Auto-generated by typewalk, vv2.0 (beta)
        # Written: Tue Mar  6 13:06:06 2018
        # Qualifying types: RAW
        # Qualifying logic: AND
        # -----------------------
        /<PATH_TO_DATA>/data/tutorials/ad_usermanual/playdata/N20170609S0154.fits
        /<PATH_TO_DATA>/data/tutorials/ad_usermanual/playdata/new154.fits



Creating New Astrodata Tags [Advanced Topic]
============================================

The |ProgManual| describes how to create new |AstroData| classes for new
instruments (specifically, see ad_tags_). This section describes the very basic
steps for a new user to create self-defined tags.

.. todo:: add example file.

The content of this section is based on the example file
:needs_replacement:`EXAMPLE FILE`. That file can be used as a full reference.

.. testsetup::

    >>> from astrodata import AstroData, TagSet, astro_data_tag

.. code-block:: python

    >>> class MyAstroData(AstroData):
    ...     @astro_data_tag
    ...     def _tag_mytag(self):
    ...         return TagSet(['MYTAG'])
    ...

The |astro_data_tag| decorator is used to identify the function as a tag
function. While not strictly necessary, it is recommended to use the
``_tag`` prefix in the function name to make it clear that it is a tag
function. When a file is opened using |open|, the |AstroData| class will
automatically call all the tag functions to determine the tags for the
|AstroData| object, and then determine if the file being opened is
appropriately tagged for the |AstroData| class. If it is not, the class is
not used to load in the object and its data; otherwise, it attempts to resolve
all known |AstroData| types to construct the appropriate instance.

|AstroData| only knows of *registered* |AstroData| class types. To register our
class, we use |factory|:

.. code-block:: python

    >>> import astrodata.factory as factory
    >>> factory.addClass(MyAstroData)
    >>> print(factory.getClasses())
    [<class 'astrodata.ad_tag_example_user.MyAstroData'>]

We now see our class is registered, and can use |open| to open a file that has
the identifying tag:

.. code-block:: python

    # Fake FITS file with a MYTAG keyword
    >>> ad = astrodata.open('mytag.fits')
    >>> ad.tags
    # {'MYTAG'}

    # Create one from scratch with the MYTAG keyword
    >>> from astrodata import create_from_scratch
    >>> from astropy.io import fits
    >>> phu = fits.PrimaryHDU(header={'MYTAG': True}).header
    >>> ad = create_from_scratch(phu)
    >>> print(ad.tags)
    # {'MYTAG'}
    >>> type(ad)
    # <class 'astrodata.ad_tag_example_user.MyAstroData'>


The tag function looks at the provided headers and if the keyword "OBSTYPE" is
set to "ARC", the tags "ARC" and "CAL" (for calibration) will be assigned to
the |AstroData| object.

.. warning::
    |Tag| functionality is primarily designed with FITS files in mind.  If you
    are extending |AstroData| to work with other data types, you will need to
    define your own tag functions that specifically handle resolving tags for
    that file type.

    This does **not** mean that you cannot use |AstroData| with other data
    types, or that it is especially difficult. It just means that you will need
    to define your own tag functions in such a way that they do not use, e.g.,
    ``self.phu`` if no such concept/equivalent exists in your desired file
    type.

A whole suite of such tag functions is needed to fully characterize all
types of data an instrument can produce. |gemini_instruments| is an
example of a package defining a number of |AstroData| types that use the
tag system to automaticlaly and precisely identify the specific instrument
used to produce the data, and to process it accordingly.

Tags should be exact and precise. For quantities and values that are
not so well defined (for example, the type of observation), descriptors
are used. For more information about descriptors, see the section on
:ref:`headers`.

For more information on creating and working with Tags, as well as developing
with/for |astrodata|, see the |ProgManual|.

.. tags.rst

.. _tags:

**************
Astrodata Tags
**************

What are the Astrodata Tags?
============================
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

As a side note, the tags are used by DRAGONS Recipe System to match recipes
and primitives to the data.

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

The tags can be used when coding.  For example::

    >>> if 'GMOS' in ad.tags:
    ...   print('I am GMOS')
    ... else:
    ...   print('I am these instead:', ad.tags)
    ...

And::

    >>> if {'IMAGE', 'GMOS'}.issubset(ad.tags):
    ...   print('I am a GMOS Image.')
    ...

Using typewalk
==============
In DRAGONS, there is a convenience tool that will list the Astrodata tags
for all the FITS file in a directory.

To try it, from the shell, not Python, go to the "playdata" directory and
run typewalk::

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
lists::

    % typewalk --tags RAW
    directory:  /data/workspace/ad_usermanual/playdata
     N20170609S0154.fits ............... (ACQUISITION) (GEMINI) (GMOS) (IMAGE) (NORTH) (RAW) (SIDEREAL) (UNPREPARED)
     new154.fits ....................... (ACQUISITION) (GEMINI) (GMOS) (IMAGE) (NORTH) (RAW) (SIDEREAL) (UNPREPARED)
    Done DataSpider.typewalk(..)

::

    % typewalk --tags RAW -o rawfiles.lis
    % cat rawfiles.lis
    # Auto-generated by typewalk, vv2.0 (beta)
    # Written: Tue Mar  6 13:06:06 2018
    # Qualifying types: RAW
    # Qualifying logic: AND
    # -----------------------
    /Users/klabrie/data/tutorials/ad_usermanual/playdata/N20170609S0154.fits
    /Users/klabrie/data/tutorials/ad_usermanual/playdata/new154.fits



Creating New Astrodata Tags [Advanced Topic]
============================================
For proper and complete instructions on how to create Astrodata Tags and
the |AstroData| class that hosts the tags, the reader is invited to refer to the
Astrodata Programmer Manual. Here we provide a simple introduction that
might help some readers better understand Astrodata Tags, or serve as a
quick reference for those who have written Astrodata Tags in the past but need
a little refresher.

The Astrodata Tags are defined in an |AstroData| class.  The |AstroData|
class specific to an instrument is located in a separate package, not in
|astrodata|. For example, for Gemini instruments, all the various |AstroData|
classes are contained in the |gemini_instruments| package.

An Astrodata Tag is a function within the instrument's |AstroData| class.
The tag function is distinguished from normal functions by applying the
:func:`~astrodata.astro_data_tag` decorator to it.
The tag function returns a :class:`astrodata.TagSet`.

For example::

    class AstroDataGmos(AstroDataGemini):
        ...
        @astro_data_tag
        def _tag_arc(self):
            if self.phu.get('OBSTYPE) == 'ARC':
                return TagSet(['ARC', 'CAL'])

The tag function looks at the headers and if the keyword "OBSTYPE" is set
to "ARC", the tags "ARC" and "CAL" (for calibration) will be assigned to the
|AstroData| object.

A whole suite of such tag functions is needed to fully characterize all
types of data an instrument can produce.

Tags are about what the dataset is, not it's flavor.  The Astrodata
"descriptors" (see the section on :ref:`headers`) will describe the flavor.
For example, tags will say that the data is an image, but the descriptor
will say whether it is B-band or R-band. Tags are used for recipe and
primitive selection.  A way to understand the difference between a tag and
a descriptor is in terms of the recipe that will be selected: A GMOS image
will use the same recipe whether it's a B-band or R-band image. However,
a GMOS longslit spectrum will need a very different recipe.  A bias is
reduced differently from a science image, there should be a tag differentiating
a bias from a science image.  (There is for GMOS.)

For more information on adding to Astrodata, see the Astrodata Programmer
Manual.
.. design.rst

.. _design:

**************
General Design
**************

Astronomical instruments come in a variety of forms, each with unique features
and requirements that are not readily transferable between different
instruments, observatories, and systems. However, there are also many
similarities between them, and the data reduction process is often similar
regardless of the instrument. The AstroData package is designed to provide a
common interface to astronomical data, regardless of the instrument that
produced it.

While at first glance this may seem counterintuitive---after all, how can a
spectrograph and a camera share the same interface?---breaking down their
common features and only developing their unique aspects once has proven to
significantly reduce the amount of code required to support each instrument. As
an example of such a system, see the Gemini Data Reduction System (|DRAGONS|),
which uses AstroData to support data from all of Gemini's instruments.

As a developer, AstroData consists of several concepts used to automatically
resolve data based on the instrument and observation type:

1. |AstroData| - This is the primary class from which all other data classes
   are derived. It is a container for the data and metadata associated with a
   single astronomical observation. It is also an iterable object, with each
   iteration returning a "slice" of the data, which is itself an AstroData
   object. This is discussed further in :ref:`ad_slices`.

2. |Tags| - These are high-level metadata that describe the observation and
   link it to the recipes required to process it. They are discussed further in
   :ref:`ad_tags`.

3. |Descriptors| - These are a way to access the metadata in a uniform manner,
   and can be used to access quantities reuiring introspection of the data
   itself.

Thee three concepts are discussed in detail in the following sections.
Together, they provide a way to access astronomical data in a uniform manner,
regardless of the instrument that produced it, while still being "aware" of any
percularities of a given instrument completely controlled by the developer.

.. note::
   Understanding the differences between AstroData objects, AstroData tags, and
   AstroData descriptors is critical to understanding and implementing to full
   range of features AstroData provides. One way to think of them is:

   1. AstroData manages data and associated metadata, which may include Tags
   and Descriptors.
   2. Tags are high-level metadata descripting the observation, observatory,
   and instrument, that AstroData uses to automatically resolve how to read in
   and process a data file.
   3. Descriptors are a way to access data not found in the metadata, or
   requiring some manipulation of the data itself to determine a given value.
   Like a python property, but without the attribute syntax (to reflect that it
   may be costly to call).

..
   As astronomical instruments have become more complex, there has been an
   increasing need for reduction packages and pipelines to deal with the specific
   needs of each instrument. Despite this complexity, many of the reduction steps
   can be very similar and the overall effort could be reduced significantly by
   sharing code. In practice, however, there are often issues regarding the manner
   in which the data are stored internally. The purpose of AstroData is to provide
   a uniform interface to the data and metadata, in a manner independent both of
   the specific instrument and the way the data are stored on disk, thereby
   facilitating this code-sharing.  It is *not* a new astronomical data format; it
   is a way to unify how those data are accessed.

   One of the main features of AstroData is the use of *descriptors*, which
   provide a level of abstraction between the metadata and the code accessing it.
   Somebody using the AstroData interface who wishes to know the exposure time of
   a particular astronomical observation represented by the AstroData object
   ``ad`` can simply write ``ad.exposure_time()`` without needing to concern
   themselves about how that value is stored internally, for example, the name of
   the FITS header keyword. These are discussed further in :ref:`ad_descriptors`.

   AstroData also provides a clearer representation of the relationships between
   different parts of the data produced from a single astronomical observation.
   Modern astronomical instruments often contain multiple detectors that are read
   out separately and the multi-extension FITS (MEF) format used by many
   institutions, including Gemini Observatory, handles the raw data well. In this
   format, each detector's data and metadata is assigned to its own extension,
   while there is also a separate extension (the Primary Header Unit, or PHU)
   containing additional metadata that applies to the entire observation. However,
   as the data are processed, more data and/or metadata may be added whose
   relationship is obscured by the limitations of the MEF format. One example is
   the creation and propagation of information describing the quality and
   uncertainty of the scientific data: while this was a feature of
   Gemini IRAF\[#iraf]_, the coding required to implement it was cumbersome.
   AstroData uses the `astropy.nddata.NDData` class, as discussed in
   :ref:`containers`. This makes the relationship between these data much clearer,
   and AstroData creates a syntax that makes readily apparent the roles of other
   data and metadata that may be created during the reduction process.

AstroData was originally designed for the Gemini Observatories, which primarily
use the FITS and FITS MEF formats for their data. While AstroData comes
out-of-the-box with FITS-specific readers and syntax, extending it to include
other file formats is straightforward. See :ref:`astrodata` for more details.

.. note::
   While there is currently only FITS support, we plan to include native asdf
   support as well in the future.

When using a FITS or FITS-like file, an AstroData object consists of one or
more self-contained "extensions" (data and metadata) plus additional data and
metadata that is relevant to all the extensions. In many data reduction
processes, the same operation will be performed on each extension (e.g.,
subtracting an overscan region from a CCD frame) and an axiom of AstroData is
that iterating over the extensions produces AstroData "slices" which retain
knowledge of the top-level data and metadata. Since a slice has one (or more)
extensions plus this top-level (meta)data, it too is an AstroData object
and, specifically, an instance of the same subclass as its parent.

..
   TODO: Need to remove the Recipe system reference as docs here and port
   anything important here. It can be used for examples, but shouldn't be the
   primary source for astrodata-relevant docs.

..
   A final feature of AstroData is the implementation of very high-level metadata.
   These data, called ``tags``, facilitate a key part of the Gemini data reduction
   system, DRAGONS, by linking the astronomical data to the recipes required to
   process them. They are explained in detail in :ref:`ad_tags` and the Recipe
   System Programmers Manual\ [#rsprogman]_.

..
   .. note::

      AstroData and DRAGONS have been developed for the reduction of data from
      Gemini Observatory, which produces data in the FITS format that is still the
      most widely-used format for astronomical data. In light of this, and the
      limited resources in the Science User Support Department, we have only
      *developed* support for FITS, even though the AstroData format is designed
      to be independent of the file format. In some cases, this has led to
      uncertainty and internal disagreement over where precisely to engage in
      abstraction and, should AstroData support a different file format, we
      may find alternative solutions that result in small, but possibly
      significant, changes to the API.


..
   .. [#iraf] `<https://www.gemini.edu/observing/phase-iii>`_

   .. [#rsprogman] |RSProgManual|

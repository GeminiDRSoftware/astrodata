.. containers.rst

.. _containers:

***************
Data Containers
***************

The AstroData package is built around the concept of data containers. These are
objects that contain the data for a single observation, and determine the
structure of these data in memory. We have extended the Astropy |NDData| class
to provide the core functionality of these containers, and added a number of
mixins to provide additional functionality.

Specifically, we extend |NDData| with the following:

* :py:class:`astrodata.NDAstroData` - the main data container class
* :py:class:`astrodata.NDAstroDataMixin` - a mixin class that adds additional functionality
  to |NDData|, such as the ability to access image planes and tables stored in
  the ``meta`` dict as attributes of the object
* :py:class:`astrodata.NDArithmeticMixin` - a mixin class that adds arithmetic functionality
* :py:class:`astrodata.NDSlicingMixin` - a mixin class that adds slicing functionality

..
  A third, and very important part of the AstroData core package is the data
  container. We have chosen to extend Astropy's |NDData| with our own
  requirements, particularly lazy-loading of data using by opening the FITS files
  in read-only, memory-mapping mode, and exploiting the windowing capability of
  `astropy.io.fits` (using ``section``) to reduce our memory requirements, which
  becomes important when reducing data (e.g., stacking).

..
  We'll describe here how we depart from |NDData|, and how do we integrate the
  data containers with the rest of the package. Please refer to |NDData| for the
  full interface.

.. _ad_nddata:

|NDAstroData| class
-------------------

Our main data container is |NDAstroData|. Fundamentally, it is
a derivative of :class:`astropy.nddata.NDData`, plus a number of mixins to add
functionality::

    class NDAstroData(AstroDataMixin, NDArithmeticMixin, NDSlicingMixin, NDData):
        ...

With these mixins, |NDAstroData| is extended to allow for ease and efficiency
of use, as if a common array, with extra features such as uncertainty
propogation and efficient slicing with typically array syntax.

Upon initialization (see |AstroData|'s :py:meth:`~astrodata.core.AstroData.__init__`
method), the |AstroData| class will attempt to open the file in memory-mapping
mode, which is the default mode for opening FITS files in Astropy. This means
that the data is not loaded into memory until it is accessed, and is discarded
from memory when it is no longer needed. This is particularly important for
large data sets common in astronomy.

Much of |NDAstrodata| acts to mimic the behavior of |NDData| and
:py:mod:`astropy.io.fits` objects, but is designed to be extensible to other
formats and means of storing, accessing, and manipulating data.

..
    Our first customization is ``NDAstroData.__init__``. It relies mostly on the
    upstream initialization, but customizes it because our class is initialized
    with lazy-loaded data wrapped around a custom class
    (`astrodata.fits.FitsLazyLoadable`) that mimics a `astropy.io.fits` HDU
    instance just enough to play along with |NDData|'s initialization code.

    NOTE: This needs to be better described, the way it works is not like the
    way it was originally described, and the caveats need to be made apparent.

.. _ad_slices:

Slicing
-------

One can already slice |NDAstroData| objects as with |NDData|, as normal Python arrays

.. testsetup::

  import astrodata

.. code-block:: python

      >>> ad = astrodata.from_file(some_fits_file)
      >>> ad.shape
      [(2048, 2048)]

      # Access pixels 100-200 in both dimensions on the first image plane.
      >>> ad.data[0][100:200, 100:200].shape
      (100, 100)

It's also useful to access specific "windows" in the data, which is implemented
in |NDAstroData| such that only the data necessary to access a window is loaded
into memory.

The :meth:`astrodata.AstroData.window` property returns an instance of
:class:`~astrodata.nddata.NDWindowing`, which only references the |AstroData|
object being windowed (i.e., it contains no direct references to the data).
|NDWindowingAstroData|, which has references
pointing to the memory mapped data requested by the window.

..
  We've added another new property, ``window``, that can be used to
  explicitly exploit the `astropy.io.fits`'s ``section`` property, to (again)
  avoid loading unneeded data to memory. This property returns an instance of
  ``NDWindowing`` which, when sliced, in turn produces an instance of
  ``NDWindowingAstroData``, itself a proxy of ``NDAstroData``. This scheme may
  seem complex, but it was deemed the easiest and cleanest way to achieve the
  result that we were looking for.

The base ``NDAstroData`` class provides the memory-mapping functionality built
upon by |NDWindowingAstroData|, with other important behaviors added by the
other mixins.

..
  The base ``NDAstroData`` class provides the memory-mapping functionality,
  with other important behaviors added by the ``AstroDataMixin``, which can
  be used with other |NDData|-like classes (such as ``Spectrum1D``) to add
  additional convenience.

One addition is the ``variance`` property, which allows direct access and
setting of the data's uncertainty, without the user needing to explicitly wrap
it as an ``NDUncertainty`` object. Internally, the variance is stored as an
``ADVarianceUncertainty`` object, which is subclassed from Astropy's standard
``VarianceUncertainty`` class with the addition of a check for negative values
whenever the array is accessed.

``NDAstroDataMixin`` also changes the default method of combining the ``mask``
attributes during arithmetic operations from ``logical_or`` to ``bitwise_or``,
since the individual bits in the mask have separate meanings.

The way slicing affects the ``wcs`` is also changed since DRAGONS regularly
uses the callable nature of ``gWCS`` objects and this is broken by the standard
slicing method.

.. todo:: Check source for where this feature is implemented and write a test
   for it.

Finally, the additional image planes and tables stored in the ``meta`` dict
are exposed as attributes of the ``NDAstroData`` object, and any image planes
that have the same shape as the parent ``NDAstroData`` object will be handled
by ``NDWindowingAstroData``. Sections will be ignored when accessing image
planes with a different shape, as well as tables.

.. note::

   We expect to make changes to ``NDAstroData`` in future releases. In particular,
   we plan to make use of the ``unit`` attribute provided by the
   |NDData| class and increase the use of memory-mapping by default. These
   changes mostly represent increased functionality and we anticipate a high
   (and possibly full) degree of backward compatibility.

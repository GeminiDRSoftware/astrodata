.. astrodata.rst

.. _astrodata:

*************************
AstroData and Derivatives
*************************

The |AstroData| class is the main interface to the package. When opening files
or creating new objects, a derivative of this class is returned, as the base
|AstroData| class is not intended to be used directly. It provides the logic to
calculate the :ref:`tag set <ad_tags>` for an image, which is common to all
data products. Aside from that, it lacks any kind of specialized knowledge
about the different instruments that produce the FITS files. More importantly,
it defines two methods (:meth:`~astrodata.AstroData.info` and
:meth:`~astrodata.AstroData.load`) that read in and offer access to
data in FITS files.  When extending to other file types, these methods should
be re-implemented.  |AstroData| also defines several useful properties and
methods for FITS files specifically, such as :meth:`astrodata.AstroData.phu`,
:meth:`astrodata.AstroData.hdr`, and :meth:`astrodata.AstroData.write`,
that should also be overridden when extending to other file types.

|AstroData| defines a common interface. Much of it consists of implementing
semantic behavior (access to components through indices, like a list;
arithmetic using standard operators; etc), mostly by implementing standard
Python methods:

* Defines a common :meth:`~astrodata.AstroData.__init__` function.

* Implements ``__deepcopy__``.

* Implements ``__iter__`` to allow sequential iteration over the main set of
  components (e.g., FITS science HDUs).

* Implements ``__getitem__`` to allow data slicing (e.g., ``ad[2:4]`` returns
  a new |AstroData| instance that contains only the third and fourth main
  components).

* Implements ``__delitem__`` to allow for data removal based on index. It does
  not define ``__setitem__``, though. The basic AstroData series of classes
  only allows to append new data blocks, not to replace them in one sweeping
  move.

* Implements ``__add__``, ``__sub__``, ``__mul__``, ``__truediv__``, and
  their in-place equivalents, based on them.

There are a few other methods. For a detailed discussion, please refer to the
:ref:`api`.

.. _tags_prop_entry:

The ``tags`` Property
=====================

Additionally, and crucial to the package, AstroData offers a ``tags`` property,
that returns a resolved set of textual tags that describe the object
represented by an instance (as a set of strings). This is useful for quickly
determining if a certain dataset belongs to an arbitrary category.

The implementation for the tags property is just a call to
``AstroData._process_tags()``. This function implements the actual logic behind
calculating the tag set (described :ref:`below <ad_tags>`). A derivative class
could override this to provide a different logic, but this is not recommended
unless there is a very good reason to do so.

For an example of how tags are resolved, seet :ref:`ad_tags`.

Writing an ``AstroData`` Derivative
===================================

We will step through the process of creating a new |AstroData| derivative.

.. creating_astrodata_derivative:

Create a new class
------------------

The first step to creating a new |AstroData| derivative is to create a new
class that inherits from |AstroData|. If the new class is intended to handle
non-FITS files, it should override the ``info`` and ``load`` methods. In this
case, we will create a class to handle the following ASCII file:

.. code-block:: text

  Wavelength (nm)  Flux (erg/cm2/s/nm)
  1.0              1.0
  2.0              1.5
  3.0              2.0
  4.0              2.5
  5.0              3.0
  6.0              2.5
  7.0              1.0

Let's create our class to just override the info and load methods, and return a
formatted string containing  the information in the header of the file when the
``AstroData.info`` method is called:

.. code-block:: python

    from astrodata import AstroData, NDAstroData

    class AstroDataMyFile(AstroData):
        _wavelength: None | NDAstroData
        _flux: None | NDAstroData
        _header: list[str]


        def __init__(self, source):
            super().__init__(source)
            self._wavelength = None
            self._flux = None
            self._header = []

        @staticmethod
        def _matches_data(source):
            return source.lower().endswith('.txt')

        def info(self) -> str:
            def batch(iterable, n=1):
                l = len(iterable)
                for ndx in range(0, l, n):
                    yield iterable[ndx:min(ndx + n, l)]

            # Just printing out information retrieved from the text file
            # header.
            return ' || '.join(
              f'{w:>10} {f:>10}'
              for w, f in batch(self._header, 2)
            )

        def load(self, path: str):
            with open(path, 'r') as f:
                # First line is the header info
                self._header = f.readline().split()

                # This should keep units with the data
                self._header = [
                  (col, unit)
                  for col, unit in zip(self._header[0::2], self._header[1::2])
                ]

                for line in f:
                      w, f = line.split()
                      self._wavelength.append(float(w))
                      self._flux.append(float(f))

We now have a class that can be used to load and store data from our ASCII
file. The ``info`` method returns a formatted string containing the header
information, and the ``load`` method reads in the data from the file. The
``_matches_data`` method is used to determine if the file is of the correct
type. In this case, we are just checking that the file extension is ``.txt``.

However, suppose we only want to use this class for files that contain
wavelength and flux information and nothing else. In that case, we can check
the header information in the ``_matches_data`` method:

.. code-block:: python

    @staticmethod
    def _matches_data(source):
        if isinstance(source, str):
            with open(source, 'r') as f:
                header = f.readline().split()

        else:
            header = source.readline().split()

        # Check that the header contains no extra information.
        if any(col not in ('Wavelength', 'Flux') for col, _ in header):
            return False

        # Check that the header contains both wavelength and flux information.
        return all(
          any(col == name for col, _ in header)
          for name in ('Wavelength', 'Flux')
        )

.. note::
  To conserve space in this document, we will only include modified code
  snippets (with any necessary context) for the rest of the examples. At the
  end of the document there will be an executable with the "final" code. Feel
  free to use this code as a template.

If there were other metadata contained in the file header, such as intrument
and mode information, we could use that to determine if the file is of the
correct type.

.. _code_organization:

Code Organization (Optional)
----------------------------

The code for our new class can be placed in a single file, but it is often
useful to organize our code into multiple files depending on their scope and
purpose.

In DRAGONS, astrodata classes for individual instruments are organized into
packages. We'll use DRAGONS' GMOS instrument as an example (see
`the DRAGONS repository <https://github.com/GeminiDRSoftware/DRAGONS/tree/master/gemini_instruments/gmos>`_
for the full code). It has the following structure:

.. code-block:: text

    gemini_instruments
        __init__.py
        gmos
            tests/
            __init__.py
            adclass.py
            lookup.py

Where ``adclass.py`` contains the ``AstroDataGmos`` class, and ``lookup.py``
contains a dictionary of filter names and their central wavelengths. The
``__init__.py`` files are used to import the classes and functions that are
needed by the package. For example, the ``gmos/__init__.py`` file contains the
following:

.. code-block:: python

    __all__ = ['AstroDataGmos']

    from astrodata import factory
    from ..gemini import addInstrumentFilterWavelengths
    from .adclass import AstroDataGmos
    from .lookup import filter_wavelengths

    factory.addClass(AstroDataGmos)
    # Use the generic GMOS name for both GMOS-N and GMOS-S
    addInstrumentFilterWavelengths('GMOS', filter_wavelengths)

``lookup.py`` contains information that is specific to the instrument but is
not explicitly required by the ``AstroDataGmos`` class. In this case, it is a
dictionary of filter names and their central wavelengths. The
``addInstrumentFilterWavelengths`` function is used to add this information to
the ``AstroDataGemini`` class, which is the parent class of ``AstroDataGmos``.
This function is defined in the ``gemini/__init__.py`` file, which is imported
by ``gmos/__init__.py``. The motivation here is to keep these lookup data
separated from the class so changes to these data are only reflected in one and
will not modify the class itself.

The ``tests/`` directory contains unit tests for the ``AstroDataGmos`` class.
Determining the nature and scale of tests is left to the developer.

..
    The first step when creating new |AstroData| derivative hierarchy would be to
    create a new class that knows how to deal with some kind of specific data in a
    broad sense.

    |AstroData| implements both ``.info()`` and ``.load()`` in ways that are
    specific to FITS files. It also introduces a number of FITS-specific methods
    and properties, e.g.:

    * The properties ``phu`` and ``hdr``, which return the primary header and
      a list of headers for the science HDUs, respectively.

    * A ``write`` method, which will write the data back to a FITS file.

    * A ``_matches_data`` **static** method, which is very important, involved in
      guiding for the automatic class choice algorithm during data loading. We'll
      talk more about this when dealing with :ref:`registering our classes
      <class_registration>`.

    It also defines the first few descriptors, which are common to all Gemini data:
    ``instrument``, ``object``, and ``telescope``, which are good examples of simple
    descriptors that just map a PHU keyword without applying any conversion.

    A typical AstroData programmer will extend this class (|AstroData|). Any of
    the classes under the ``gemini_instruments`` package can be used as examples,
    but we'll describe the important bits here.


    Create a package for it
    -----------------------

    This is not strictly necessary, but simplifies many things, as we'll see when
    talking about *registration*. The package layout is up to the designer, so you
    can decide how to do it. For DRAGONS we've settled on the following
    recommendation for our internal process (just to keep things familiar)::

        gemini_instruments
            __init__.py
            instrument_name
                __init__.py
                adclass.py
                lookup.py

    Where ``instrument_name`` would be the package name (for Gemini we group all
    our derivative packages under ``gemini_instruments``, and we would import
    ``gemini_instruments.gmos``, for example). ``__init__.py`` and ``adclass.py``
    would be the only required modules under our recommended layout, with
    ``lookup.py`` being there just to hold hard-coded values in a module separate
    from the main logic.

    ``adclass.py`` would contain the declaration of the derivative class, and
    ``__init__.py`` will contain any code needed to register our class with the
    |AstroData| system upon import.


    Create your derivative class
    ----------------------------

    This is an excerpt of a typical derivative module::

        from astrodata import astro_data_tag, astro_data_descriptor, TagSet
        from astrodata import AstroData

        from . import lookup

        class AstroDataInstrument(AstroData):
            __keyword_dict = dict(
                array_name = 'AMPNAME',
                array_section = 'CCDSECT'
            )

            @staticmethod
            def _matches_data(source):
                return source[0].header.get('INSTRUME', '').upper() == 'MYINSTRUMENT'

            @astro_data_tag
            def _tag_instrument(self):
              return TagSet(['MYINSTRUMENT'])

            @astro_data_tag
            def _tag_image(self):
                if self.phu.get('GRATING') == 'MIRROR':
                    return TagSet(['IMAGE'])

            @astro_data_tag
            def _tag_dark(self):
                if self.phu.get('OBSTYPE') == 'DARK':
                    return TagSet(['DARK'], blocks=['IMAGE', 'SPECT'])

            @astro_data_descriptor
            def array_name(self):
                return self.phu.get(self._keyword_for('array_name'))

            @astro_data_descriptor
            def amp_read_area(self):
                ampname = self.array_name()
                detector_section = self.detector_section()
                return "'{}':{}".format(ampname, detector_section)

    .. note::
      An actual Gemini Facility Instrument class will derive from
      ``gemini_instruments.AstroDataGemini``, but this is irrelevant
      for the example.

    The class typically relies on functionality declared elsewhere, in some
    ancestor, e.g., the tag set computation and the ``_keyword_for`` method are
    defined at |AstroData|.

Some highlights:

* ``__keyword_dict``\ [#keywdict]_ defines one-to-one mappings, assigning a more
  readable moniker for an HDU header keyword. The idea here is to prevent
  hard-coding the names of the keywords, in the actual code. While these are
  typically quite stable and not prone to change, it's better to be safe than
  sorry, and this can come in useful during instrument development, which is
  the more likely source of instability. The actual value can be extracted by
  calling ``self._keyword_for('moniker')``.

* ``_matches_data`` is a static method. It does not have any knowledge about
  the class itself, and it does not work on an *instance* of the class: it's
  a member of the class just to make it easier for the AstroData registry to
  find it. This method is passed some object containing cues of the internal
  structure and contents of the data. This could be, for example, an instance
  of ``HDUList``. Using these data, ``_matches_data`` must return a boolean,
  with ``True`` meaning "I know how to handle this data".

  Note that ``True`` **does not mean "I have full knowledge of the data"**. It
  is acceptable for more than one class to claim compatibility. For a GMOS FITS
  file, the classes that will return ``True`` are: |AstroData| (because it is
  a FITS file that comply with certain minimum requirements),
  `~gemini_instruments.gemini.AstroDataGemini` (the data contains Gemini
  Facility common metadata), and `~gemini_instruments.gmos.AstroDataGmos` (the
  actual handler!).

  But this does not mean that multiple classes can be valid "final" candidates.
  If AstroData's automatic class discovery finds more than one class claiming
  matching with the data, it will start discarding them on the basis of
  inheritance: any class that appears in the inheritance tree of another one is
  dropped, because the more specialized one is preferred. If at some point the
  algorithm cannot find more classes to drop, and there is more than one left
  in the list, an exception will occur, as AstroData will have no way to choose
  one over the other.

* A number of "tag methods" have been declared. Their naming is a convention,
  at the end of the day (the "``_tag_``" prefix, and the related "``_status_``"
  one, are *just hints* for the programmer): each team should establish
  a convention that works for them. What is important here is to **decorate**
  them using `~astrodata.astro_data_tag`, which earmarks the method so that it
  can be discovered later, and ensures that it returns an appropriate value.

  A tag method will return either a `~astrodata.TagSet` instance (which can be
  empty), or ``None``, which is the same as returning an empty
  `~astrodata.TagSet`\ [#tagset1]_.

  **All** these methods will be executed when looking up for tags, and it's up
  to the tag set construction algorithm (see :ref:`ad_tags`) to figure out the final
  result.  In theory, one **could** provide *just one* big method, but this is
  feasible only when the logic behind deciding the tag set is simple. The
  moment that there are a few competing alternatives, with some conditions
  precluding other branches, one may end up with a rather complicated dozens of
  lines of logic. Let the algorithm do the heavy work for you: split the tags
  as needed to keep things simple, with an easy to understand logic.

  Also, keeping the individual (or related) tags in separate methods lets you
  exploit the inheritance, keeping common ones at a higher level, and
  redefining them as needed later on, at derived classes.

  Please, refer to `~gemini_instruments.gemini.AstroDataGemini`,
  `~gemini_instruments.gmos.AstroDataGmos`, and
  `~gemini_instruments.gnirs.AstroDataGnirs` for examples using most of the
  features.

* The `astrodata.AstroData.read` method calls the `astrodata.fits.read_fits`
  function, which uses metadata in the FITS headers to determine how the data
  should be stored in the |AstroData| object. In particular, the ``EXTNAME``
  and ``EXTVER`` keywords are used to assign individual FITS HDUs, using the
  same names (``SCI``, ``DQ``, and ``VAR``) as Gemini-IRAF for the ``data``,
  ``mask``, and ``variance`` planes.  A ``SCI`` HDU *must* exist if there is
  another HDU with the same ``EXTVER``, or else an error will occur.

  If the raw data do not conform to this format, the `astrodata.AstroData.read`
  method can be overridden by your class, by having it call the
  `astrodata.fits.read_fits` function with an additional parameter,
  ``extname_parser``, that provides a function to modify the header. This
  function will be called on each HDU before further processing. As an example,
  the SOAR Adaptive Module Imager (SAMI) instrument writes raw data as
  a 4-extension MEF file, with the extensions having ``EXTNAME`` values
  ``im1``, ``im2``, etc. These need to be modified to ``SCI``, and an
  appropriate ``EXTVER`` keyword added` [#extver]_\. This can be done by
  writing a suitable ``read`` method for the ``AstroDataSami`` class::

    @classmethod
    def read(cls, source, extname_parser=None):
        def sami_parser(hdu):
            m = re.match('im(\d)', hdu.header.get('EXTNAME', ''))
            if m:
                hdu.header['EXTNAME'] = ('SCI', 'Added by AstroData')
                hdu.header['EXTVER'] = (int(m.group(1)), 'Added by AstroData')

        return super().read(source, extname_parser=extname_parser)


* *Descriptors* will make the bulk of the class: again, the name is arbitrary,
  and it should be descriptive. What *may* be important here is to use
  `~astrodata.astro_data_descriptor` to decorate them. This is *not required*,
  because unlike tag methods, descriptors are meant to be called explicitly by
  the programmer, but they can still be marked (using this decorator) to be
  listed when calling the ``descriptors`` property. The decorator does not
  alter the descriptor input or output in any way, so it is always safe to use
  it, and you probably should, unless there's a good reason against it (e.g.,
  if a descriptor is deprecated and you don't want it to show up in lookups).

  More detailed information can be found in :ref:`ad_descriptors`.


.. _class_registration:

Register your class
-------------------

Finally, you need to include your class in the **AstroData Registry**. This is
an internal structure with a list of all the |AstroData|\-derived classes that
we want to make available for our programs. Including the classes in this
registry is an important step, because a file should be opened using
`astrodata.from_file` or `astrodata.create_from_scratch`, which uses the
registry to identify the appropriate class (via the ``_matches_data`` methods),
instead of having the user specify it explicitly.

A typical ``__init__.py`` file on an instrument package (example above) will
look like this::

    __all__ = ['AstroDataMyInstrument']

    from astrodata import factory
    from .adclass import AstroDataMyInstrument

    factory.add_class(AstroDataMyInstrument)

The call to ``factory.add_class`` is the one registering the class. This step
**needs** to be done **before** the class can be used effectively in the
AstroData system. Placing the registration step in the ``__init__.py`` file is
convenient, because importing the package will be enough!

Thus, a script making use of DRAGONS' AstroData to manipulate GMOS data
could start like this::

    import astrodata
    from gemini_instruments import gmos

    ...

    ad = astrodata.open(some_file)

The first import line is not needed, technically, because the ``gmos`` package
will import it too, anyway, but we'll probably need the ``astrodata`` package
in the namespace anyway, and it's always better to be explicit. Our
typical DRAGONS scripts and modules start like this, instead::

    import astrodata
    import gemini_instruments

``gemini_instruments`` imports all the packages under it, making knowledge
about all Gemini instruments available for the script, which is perfect for a
multi-instrument pipeline, for example. Loading all the instrument classes is
not typically a burden on memory, though, so it's easier for everyone to take
the more general approach. It also makes things easier on the end user, because
they won't need to know internal details of our packages (like their naming
scheme). We suggest this "*cascade import*" scheme for all new source trees,
letting the user decide which level of detail they need.

As an additional step, the ``__init__.py`` file in a package may do extra
initialization. For example, for the Gemini modules, one piece of functionality
that is shared across instruments is a descriptor that translates a filter's
name (say "u" or "FeII") to its central wavelength (e.g.,
0.35µm, 1.644µm). As it is a rather common function for us, it is implemented
by `~gemini_instruments.gemini.AstroDataGemini`. This class **does not know**
about its daughter classes, though, meaning that it **cannot know** about the
filters offered by their instruments. Instead, we offer a function that can
be used to update the filter → wavelength mapping in
`gemini_instruments.gemini.lookup` so that it is accessible by the
`~gemini_instruments.gemini.AstroDataGemini`\-level descriptor. So our
``gmos/__init__.py`` looks like this::

    __all__ = ['AstroDataGmos']

    from astrodata import factory
    from ..gemini import addInstrumentFilterWavelengths
    from .adclass import AstroDataGmos
    from .lookup import filter_wavelengths

    factory.addClass(AstroDataGmos)
    # Use the generic GMOS name for both GMOS-N and GMOS-S
    addInstrumentFilterWavelengths('GMOS', filter_wavelengths)

where `~gemini_instruments.gemini.addInstrumentFilterWavelengths` is provided
by the ``gemini`` package to perform the update in a controlled way.

We encourage package maintainers and creators to follow such explicit
initialization methods, driven by the modules that add functionality
themselves, as opposed to active discovery methods on the core code. This
favors decoupling between modules, which is generally a good idea.

.. rubric:: Footnotes

.. [#keywdict] The keyword dictionary is a "private" property of the
   class (due to the double-underscore prefix). Each class can define its own
   set, which will not be replaced by derivative classes. ``_keyword_for`` is
   aware of this and will look up each class up the inheritance chain, in turn,
   when looking up for keywords.

.. [#tagset1] The example functions will return only
   a `~astrodata.TagSet`, if appropriate. This is OK, remember that *every
   function* in Python returns a value, which will be ``None``, implicitly, if
   you don't specify otherwise.

.. [#extver] An ``EXTVER`` keyword is not explicitly required; the
   `astrodata.fits.read_fits` method will assign the lowest available integer
   to a ``SCI`` header with no ``EXTVER`` keyword (or if its value is -1). But
   we wish to be able to identify the original ``im1`` header by assigning it
   an ``EXTVER`` of 1, etc.

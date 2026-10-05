.. descriptors.rst

.. _ad_descriptors:

***********
Descriptors
***********

Descriptors are regular methods that translate metadata from the raw
data (e.g., cards from FITS headers) to values useful for the user,
potentially doing some processing in between. They exist to:

* Abstract the actual organization of the metadata, with arbitrarily complex
  processing to generate a useful value. These abstractions can be modified
  to be instrument-specific.

* Provide a common interface to a set of instruments. This simplifies user
  training (no need to learn a different API for each instrument), and
  facilitates the reuse of code for pipelines and data processing.

* They can be used to directly translate character-limited FITS header keywords
  into more descriptive names of arbitrary length.

Descriptors **should** be decorated using `~astrodata.astro_data_descriptor`.
The only function of this decorator is to ensure that the descriptor is marked
as such: it does not alter its input or output in any way. This lets the user
explore the API of an |AstroData| object via the
`~astrodata.AstroData.descriptors` property. Here's an example of how we could
use a descriptor to build a simple class on top of the |AstroData| base class:

.. code::python
    from astrodata import AstroData, astro_data_descriptor

    class DescAstroData(AstroData):
        @astro_data_descriptor
        def airmass(self):
            '''Retrieves the airmass stored in a PHU entry'''
            return self.phu['AIRMASS']

        @astro_data_descriptor
        def total_exposure_time(self):
            '''Retrieves the total exposure time from the headers.'''
            return sum([ext.hdr['EXPTIME'] for ext in self])

    ad = DescAstroData()
    print(ad.descriptors)
    # ('airmass', 'total_exposure_time')

.. note::
  The above example is oversimplified, and would only work with a fits file
  containing these keywords. In practice, an |AstroData| extension like this
  would be specific to an instrument/file format that would be resolved using
  tags.

Descriptors **can** be decorated with :func:`~astrodata.core.returns_list` to
eliminate the need to code some logic. Some descriptors return single values,
while some return lists, one per extension. Typically, the former
descriptors refer calues associated with an entire observation (and, for MEF
files, are usually extracted from metadata in the PHU, such as ``airmass``),
while the latter descriptors where different extensions might return
different values (and typically come from metadata in the individual HDUs, such
as ``gain``).  A list is returned even if there is only one extension in the
|AstroData| object, as this allows code to be written generically to iterate
over the |AstroData| object and the descriptor return, without needing to know
how many extensions there are.

The `~astrodata.core.returns_list` decorator ensures that the descriptor
returns an appropriate object (value or list), using the following rules
to avoid unexpected behavior/confusing errors:

* If the |AstroData| object is not a single slice:

  * If the undecorated descriptor returns a list, an exception is raised
    if the list is not the same length as the number of extensions.
  * If the undecorated descriptor returns a single value, the decorator
    will turn it into a list of the correct length by copying this value.

* If the |AstroData| object is a single slice and the undecorated
  descriptor returns a list, only the first element is returned.

An example of the use of this decorator is the NIRI
`~gemini_instruments.niri.AstroDataNiri.gain` descriptor, which reads the
value from a lookup table and simply returns it.  A single value is only
appropriate if the |AstroData| object is singly-sliced and the decorator ensures
that a list is returned otherwise.

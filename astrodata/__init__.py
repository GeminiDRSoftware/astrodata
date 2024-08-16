"""Entry point for the |astrodata| package.

This package adds an abstraction layer to astronomical data by parsing the
information contained in the headers as attributes. To do so, one must subclass
:class:`astrodata.AstroData` and add parse methods accordingly to the
:class:`~astrodata.TagSet` received.

For more information, you can build the documentation locally by running

.. code-block:: bash

    nox -s docs

and opening the file ``_build/html/index.html`` in a browser. Alternatively,
you can check the online documentation at
`the |astrodata| pages site <https://geminidrsoftware.github.io/astrodata/>`_.
"""

import importlib.metadata

from . import testing
from .adfactory import AstroDataError, AstroDataFactory
from .core import AstroData
from .fits import add_header_to_table
from .nddata import AstroDataMixin, NDAstroData
from .utils import (
    Section,
    TagSet,
    astro_data_descriptor,
    astro_data_tag,
    deprecated,
    returns_list,
)

__version__ = importlib.metadata.version("astrodata")


def version():
    """Return the version of astrodata."""
    return __version__


__all__ = [
    "AstroData",
    "AstroDataError",
    "AstroDataMixin",
    "NDAstroData",
    "Section",
    "TagSet",
    "__version__",
    "add_header_to_table",
    "astro_data_descriptor",
    "astro_data_tag",
    "from_file",
    "create",
    "returns_list",
    "version",
    "testing",
    # Below this are deprecated
    "open",
]

# Make sure __all__does not have duplicates
if len(__all__) != len(set(__all__)):
    duplicates = [x for i, x in enumerate(__all__) if x in __all__[:i]]
    raise ValueError(f"Duplicate entries in __all__: {', '.join(duplicates)}")

factory = AstroDataFactory()

# Let's make sure that there's at least one class that matches the data
# (if we're dealing with a FITS file)
factory.add_class(AstroData)


def from_file(*args, **kwargs):
    """Return an |AstroData| object from a file.

    Arguments
    ---------
    source: str, os.PathLike or HDUList
        The path to the file or the HDUList object. If a string is passed, it
        will be treated as a path to a file.

    Returns
    -------
    AstroData
        An instantiated object. It will be a subclass of |AstroData|.

    Notes
    -----
    For implementation details, see
    :py:meth:`~astrodata.AstroDataFactory.get_astro_data`.

    This function is a wrapper around the factory method
    :py:meth:`~astrodata.AstroDataFactory.get_astro_data`, and uses the
    default factory instance at :py:attr:`~astrodata.factory`. If you want to
    override the default factory, you can create a new instance of
    :py:class:`~astrodata.AstroDataFactory` and use its methods directly, or
    assign it to :py:attr:`~astrodata.factory`.

    Example
    -------

    >>> from astrodata import from_file
    >>> ad = from_file("path/to/file.fits")

    Alternatively, you can use an :py:class:`~astropy.io.fits.HDUList` object:

    >>> from astropy.io import fits
    >>> hdulist = fits.open("path/to/file.fits")
    >>> ad = from_file(hdulist)

    Which can be useful for inspecting input before creating the |AstroData|
    object. This will not use the normal |AstroData| lazy-loading mechanism,
    however.
    """
    return factory.get_astro_data(*args, **kwargs)


def create(*args, **kwargs):
    """Return an |AstroData| object from data.

    Arguments
    ---------
    phu : `fits.PrimaryHDU` or `fits.Header` or `dict` or `list`
        FITS primary HDU or header, or something that can be used to create
        a fits.Header (a dict, a list of "cards").

    extensions : list of HDUs
        List of HDU objects.

    Returns
    -------
    `astrodata.AstroData`
        An AstroData instance.

    Raises
    ------
    ValueError
        If ``phu`` is not a valid object.

    Example
    -------

    >>> from astrodata import create
    >>> ad = create(phu=fits.PrimaryHDU(), extensions=[fits.ImageHDU()])
    """
    return factory.create_from_scratch(*args, **kwargs)


# Without raising a warning or error.
@deprecated(
    "Use 'astrodata.from_file'. astrodata.open is deprecated, "
    "and will be removed in a future version. They take the "
    "same arguments and return the same object.",
)
def open(*args, **kwargs):  # pylint: disable=redefined-builtin
    """Return an |AstroData| object from a file.

    .. warning::
        This function is deprecated and will be removed in a future version.
        Use :py:func:`~astrodata.from_file` instead.
    """
    return from_file(*args, **kwargs)

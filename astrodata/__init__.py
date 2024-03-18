"""This package adds an abstraction layer to astronomical data by parsing the
information contained in the headers as attributes. To do so, one must subclass
:class:`astrodata.AstroData` and add parse methods accordingly to the
:class:`~astrodata.TagSet` received.

"""
from .core import AstroData
from .adfactory import AstroDataFactory, AstroDataError
from .fits import add_header_to_table
from .nddata import NDAstroData, AstroDataMixin
from .utils import (
    Section,
    TagSet,
    astro_data_descriptor,
    astro_data_tag,
    returns_list,
    deprecated,
)

import importlib.metadata


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

    For implementation details, see
    :meth:`~astrodata.AstroDataFactory.get_astro_data`.
    """
    return factory.get_astro_data(*args, **kwargs)


def create(*args, **kwargs):
    """Return an |AstroData| object from data.

    For implementation details, see
    :meth:`~astrodata.AstroDataFactory.create_from_scratch`
    """
    return factory.create_from_scratch(*args, **kwargs)


# Without raising a warning or error.
@deprecated(
    "Use 'astrodata.from_file'. astrodata.open is deprecated, "
    "and will be removed in a future version."
)
def open(*args, **kwargs):  # pylint: disable=redefined-builtin
    """Return an |AstroData| object from a file (deprecated, use
    :func:`~astrodata.from_file`).
    """
    return from_file(*args, **kwargs)

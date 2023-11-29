"""This package adds an abstraction layer to astronomical data by parsing the
information contained in the headers as attributes. To do so, one must subclass
:class:`astrodata.AstroData` and add parse methods accordingly to the
:class:`~astrodata.TagSet` received.

.. |AstroData| replace:: :class:`~astrodata.AstroData`
.. |AstroDataError| replace:: :class:`~astrodata.AstroDataError`
.. |AstroDataMixin| replace:: :class:`~astrodata.AstroDataMixin`
.. |NDAstroData| replace:: :class:`~astrodata.NDAstroData`
.. |Section| replace:: :class:`~astrodata.Section`
.. |TagSet| replace:: :class:`~astrodata.TagSet`
.. |astro_data_descriptor| replace:: :func:`~astrodata.astro_data_descriptor`
.. |astro_data_tag| replace:: :func:`~astrodata.astro_data_tag`
.. |create| replace:: :func:`~astrodata.create`
.. |open| replace:: :func:`~astrodata.open`
.. |return_list| replace:: :func:`~astrodata.return_list`
.. |version| replace:: :func:`~astrodata.version`
"""

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
    "open",
    "returns_list",
    "version",
]


from .core import AstroData
from .factory import AstroDataFactory, AstroDataError
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
from ._version import version

__version__ = version()

factory = AstroDataFactory()
# Let's make sure that there's at least one class that matches the data
# (if we're dealing with a FITS file)
factory.add_class(AstroData)


# TODO: Need to replace this with a name that doesn't override the builtin.
# This makes it so that the following will cause unexpected behavior:
#     from astrodata import *
#     file_stream = open("some_file.fits")
# Without raising a warning or error.
@deprecated(
    "Use 'astrodata.from_file'. astrodata.open is deprecated, "
    "and will be removed in a future version."
)
def open(*args, **kwargs):  # pylint: disable=redefined-builtin
    """Return an |AstroData| object from a file."""
    return factory.get_astro_data(*args, **kwargs)


from_file = factory.get_astro_data
create = factory.create_from_scratch

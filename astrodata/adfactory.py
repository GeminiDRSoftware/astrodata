"""Factory for AstroData objects."""

import copy
import logging
import os
from contextlib import contextmanager
from copy import deepcopy

from astropy.io import fits

from .utils import deprecated

LOGGER = logging.getLogger(__name__)


class AstroDataError(Exception):
    """Exception raised when there is a problem with the AstroData class."""


class AstroDataFactory:
    """Factory class for AstroData objects."""

    _file_openers = (fits.open,)

    def __init__(self):
        self._registry = set()

    @property
    def registry(self):
        """Return the registry of classes."""
        # Shallow copy -- just don't want the set to be modified, but the
        # classes don't need to be copied.
        return copy.copy(self._registry)

    @staticmethod
    @deprecated(
        "Renamed to _open_file, please use that method instead: "
        "astrodata.factory.AstroDataFactory._open_file"
    )
    @contextmanager
    def _openFile(source):  # noqa
        return AstroDataFactory._open_file(source)

    @staticmethod
    @contextmanager
    def _open_file(source):
        """Open a file and return an appropriate object.

        Internal static method that takes a ``source``, assuming that it is
        a string pointing to a file to be opened.

        If this is the case, it will try to open the file and return an
        instance of the appropriate native class to be able to manipulate it
        (eg. ``HDUList``).

        If ``source`` is not a string, it will be returned verbatim, assuming
        that it represents an already opened file.
        """
        if isinstance(source, (str, os.PathLike)):
            # Check that the file exists.
            if not os.path.isfile(source):
                raise FileNotFoundError(f"Path is not a file: {source}")

            # Check that the file has nonzero size.
            stats = os.stat(source)

            if stats.st_size == 0:
                LOGGER.warning("File %s is zero size", source)

            if not AstroDataFactory._file_openers:
                raise AstroDataError(
                    "No file openers registered. Register some using"
                    " 'add_class' method."
                )

            # try vs all handlers
            for func in AstroDataFactory._file_openers:
                try:
                    fp = func(source)
                    yield fp

                # Catch keyboard interrupts and re-raise them.
                except KeyboardInterrupt:
                    raise

                except Exception as err:  # noqa
                    LOGGER.error(
                        "Failed to open %s with %s, got error: %s",
                        source,
                        func,
                        err,
                    )

                    # Handle nonexistent files.
                    if isinstance(err, FileNotFoundError):
                        raise err

                else:
                    if hasattr(fp, "close"):
                        fp.close()

                    return

            raise AstroDataError(
                f"No access, or not supported format for: {source}"
            )

        yield source

    @deprecated(
        "Renamed to add_class, please use that method instead: "
        "astrodata.factory.AstroDataFactory.add_class"
    )
    def addClass(self, cls):  # noqa
        """Add a new class to the |AstroDataFactory| registry.

        It will be used when instantiating an AstroData class for a FITS file.
        """
        self.add_class(cls)

    def add_class(self, cls):
        """Add a new class to the |AstroDataFactory|'s registry.

        Add a new class to the |AstroDataFactory| registry. It will be used
        when instantiating an |AstroData| class for a FITS file.
        """
        if not hasattr(cls, "_matches_data"):
            raise AttributeError(
                f"Class '{cls.__name__}' has no '_matches_data' method"
            )

        self._registry.add(cls)

    def remove_class(self, cls: type | str):
        """Remove a class from the AstroDataFactory registry."""
        if isinstance(cls, str):
            cls = next((c for c in self._registry if c.__name__ == cls), None)

        self._registry.remove(cls)

    @deprecated(
        "Renamed to get_astro_data, please use that method instead: "
        "astrodata.factory.AstroDataFactory.get_astro_data"
    )
    def getAstroData(self, source):  # noqa
        """Return an |AstroData| instance from a file or HDUList.

        Deprecated, see |get_astro_data|.
        """
        self.get_astro_data(source)

    def get_astro_data(self, source):
        """Return an |AstroData| instance from a file or HDUList.

        Takes either a string (with the path to a file) or an HDUList as
        input, and tries to return an AstroData instance.

        It will raise exceptions if the file is not found, or if there is no
        match for the HDUList, among the registered AstroData classes.

        Returns an instantiated object, or raises AstroDataError if it was
        not possible to find a match

        Arguments
        ---------
        source : `str` or `pathlib.Path` or `fits.HDUList`
            The file path or HDUList to read.

        Returns
        -------
        `astrodata.AstroData`
            An AstroData instance.
        """
        candidates = []
        with self._open_file(source) as opened:
            for adclass in self._registry:
                try:
                    if adclass.matches_data(opened):
                        candidates.append(adclass)

                except KeyboardInterrupt:
                    raise

                except Exception as err:
                    LOGGER.error(
                        "Failed to open %s with %s, got error: %s",
                        source,
                        adclass,
                        err,
                    )

        # For every candidate in the list, remove the ones that are base
        # classes for other candidates. That way we keep only the more
        # specific ones.
        final_candidates = []

        for cnd in candidates:
            if any(cnd in x.mro() for x in candidates if x != cnd):
                continue

            final_candidates.append(cnd)

        if len(final_candidates) > 1:
            raise AstroDataError(
                f"More than one class is candidate for this dataset: "
                f"{', '.join((str(s) for s in final_candidates))}"
            )

        if not final_candidates:
            raise AstroDataError("No class matches this dataset")

        return final_candidates[0].read(source)

    @deprecated(
        "Renamed to create_from_scratch, please use that method instead: "
        "astrodata.factory.AstroDataFactory.create_from_scratch"
    )
    def createFromScratch(
        self,
        phu,
        extensions=None,
    ):  # noqa
        """Create an AstroData object from a collection of objects.

        Deprecated, see |create_from_scratch|.
        """
        self.create_from_scratch(phu=phu, extensions=extensions)

    def create_from_scratch(self, phu, extensions=None):
        """Create an AstroData object from a collection of objects.

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
        """
        lst = fits.HDUList()
        if phu is not None:
            if isinstance(phu, fits.PrimaryHDU):
                lst.append(deepcopy(phu))

            elif isinstance(phu, fits.Header):
                lst.append(fits.PrimaryHDU(header=deepcopy(phu)))

            elif isinstance(phu, (dict, list, tuple)):
                p = fits.PrimaryHDU()
                p.header.update(phu)
                lst.append(p)

            else:
                raise ValueError(
                    "phu must be a PrimaryHDU or a valid header object"
                )

        if extensions is not None:
            for ext in extensions:
                lst.append(ext)

        return self.get_astro_data(lst)

"""Core module of the AstroData package, containing the |AstroData| class."""

import inspect
import logging
import os
import re
import textwrap
import warnings
from collections import OrderedDict
from contextlib import suppress
from copy import deepcopy
from functools import partial

import numpy as np
from astropy.io import fits
from astropy.nddata import NDData
from astropy.table import Table
from astropy.utils import format_doc

from .fits import (
    DEFAULT_EXTENSION,
    FitsHeaderCollection,
    _process_table,
    read_fits,
    write_fits,
)
from .nddata import ADVarianceUncertainty, NDAstroData
from .utils import (
    assign_only_single_slice,
    astro_data_descriptor,
    deprecated,
    normalize_indices,
    returns_list,
)

NO_DEFAULT = object()


_ARIT_DOC = """
    Performs {name} by evaluating ``self {op} operand``.

    Arguments
    ---------
    oper : number or object
        The operand to perform the operation  ``self {op} operand``.

    Returns
    --------
    `AstroData` instance
"""


class AstroData:
    """Base class for the AstroData software package.

    It provides an interface to manipulate astronomical data sets.

    Arguments
    ---------
    nddata : `astrodata.NDAstroData` or list of `astrodata.NDAstroData`
        List of NDAstroData objects.

    tables : dict[name, `astropy.table.Table`]
        Dict of table objects.

    phu : `astropy.io.fits.Header`
        Primary header.

    indices : list of int
        List of indices mapping the `astrodata.NDAstroData` objects that this
        object will access to. This is used when slicing an object, then the
        sliced AstroData will have the ``.nddata`` list from its parent and
        access the sliced NDAstroData through this list of indices.


    .. warning::

        This class is not meant to be instantiated directly. Instead, use the
        factory method :py:func:`astrodata.from_file` to create an instance of
        this class using a file. Alternatively, use the
        :py:meth:`astrodata.create` function to create a new instance from
        scratch.

        The documentation here is meant for developers who want to extend the
        functionality of this class.

    Registering an |AstroData| subclass
    -----------------------------------

    To create a new subclass of |AstroData|, you need to register it with the
    factory. This is done by creating a new subclass and using
    :py:meth:`AstroDataFactory.add_class`:

    .. code-block:: python

        from astrodata import AstroData, factory

        class MyAstroData(AstroData):
            @classmethod
            def _matches_data(cls):
                '''Trivial match for now.'''
                return True

        factory.add_class(MyAstroData)

    Once the class is registered, the factory will be able to create instances
    of it when reading files. It will also be able to create instances of it
    when using the :py:meth:`astrodata.create` function. It uses the special,
    required method :py:meth:`~astrodata.AstroData._matches_data` to determine
    if the class matches the data in the file. If there are multiple matches,
    the factory will try to find one that has the most specific match and is
    a subclass of the other candidates.

    If There is no match or multiple matches, the factory will raise an
    exception. See :py:meth:`AstroDataFactory.get_astro_data` for more
    information.
    """

    # TODO(teald): Docstring for AstroData has a bad lin to AstroDataFactory

    # Derived classes may provide their own __keyword_dict. Being a private
    # variable, each class will preserve its own, and there's no risk of
    # overriding the whole thing
    __keyword_dict = {
        "instrument": "INSTRUME",
        "object": "OBJECT",
        "telescope": "TELESCOP",
        "ut_date": "DATE-OBS",
    }

    def __init__(
        self, nddata=None, tables=None, phu=None, indices=None, is_single=False
    ):
        if nddata is None:
            nddata = []

        # Check that nddata is either a single or iterable of NDAstroData
        # objects
        is_nddata = isinstance(nddata, NDAstroData)

        try:
            is_nddata_iterable = isinstance(nddata[0], NDAstroData)

        except IndexError:
            # Fall back on checking if it's a list or tuple---could be empty.
            is_nddata_iterable = isinstance(nddata, (list, tuple))

        if not (is_nddata or is_nddata_iterable):
            raise TypeError(
                f"nddata must be an NDAstroData object or a list of "
                f"NDAstroData objects, not {type(nddata)} ({nddata})."
            )

        # If nddata is a single NDAstroData object, make it a list.
        if not is_nddata_iterable:
            nddata = [nddata]

        # _all_nddatas contains all the extensions from the original file or
        # object.  And _indices is used to map extensions for sliced objects.
        self._all_nddatas = nddata
        self._indices = indices

        self.is_single = is_single

        if tables is not None and not isinstance(tables, dict):
            raise ValueError("tables must be a dict")

        self._tables = tables or {}

        self._phu = phu or fits.Header()
        self._fixed_settable = {
            "data",
            "uncertainty",
            "mask",
            "variance",
            "wcs",
            "path",
            "filename",
        }
        self._logger = logging.getLogger(__name__)
        self._orig_filename = None
        self._path = None

    def __deepcopy__(self, memo):
        """Return a new instance of this class.

        Arguments
        ---------
        memo : dict
            See the documentation on `deepcopy` for an explanation on how
            this works.

        """
        obj = self.__class__()

        for attr in ("_phu", "_path", "_orig_filename", "_tables"):
            obj.__dict__[attr] = deepcopy(self.__dict__[attr])

        obj.__dict__["_all_nddatas"] = [deepcopy(nd) for nd in self._nddata]
        return obj

    def _keyword_for(self, name):
        """Return the FITS keyword name associated to ``name``.

        Arguments
        ---------
        name : str
            The common "key" name for which we want to know the associated
            FITS keyword.

        Returns
        -------
        str
            The desired keyword name.

        Raises
        ------
        AttributeError
            If there is no keyword for the specified ``name``.

        """
        for cls in self.__class__.mro():
            with suppress(AttributeError, KeyError):
                # __keyword_dict is a mangled variable
                return getattr(self, f"_{cls.__name__}__keyword_dict")[name]

        raise AttributeError(f"No match for '{name}'")

    def _process_tags(self):
        """Return the tag set (as a set of str) for the current instance."""
        results = []
        # Calling inspect.getmembers on `self` would trigger all the
        # properties (tags, phu, hdr, etc.), and that's undesirable. To
        # prevent that, we'll inspect the *class*.
        members = inspect.getmembers(
            self.__class__, lambda x: hasattr(x, "tag_method")
        )

        for _, method in members:
            ts = method(self)
            if ts.add or ts.remove or ts.blocks:
                results.append(ts)

        # Sort by the length of substractions... those that substract
        # from others go first
        results = sorted(
            results, key=lambda x: len(x.remove) + len(x.blocks), reverse=True
        )

        # Sort by length of blocked_by, those that are never disabled go first
        results = sorted(results, key=lambda x: len(x.blocked_by))

        # Sort by length of if_present... those that need other tags to
        # be present go last
        results = sorted(results, key=lambda x: len(x.if_present))

        tags = set()
        removals = set()
        blocked = set()
        for plus, minus, blocked_by, blocks, is_present in results:
            if is_present:
                # If this TagSet requires other tags to be present, make
                # sure that all of them are. Otherwise, skip...
                if len(tags & is_present) != len(is_present):
                    continue

            allowed = (len(tags & blocked_by) + len(plus & blocked)) == 0
            if allowed:
                # This set is not being blocked by others...
                removals.update(minus)
                tags.update(plus - removals)
                blocked.update(blocks)

        return tags

    @classmethod
    def matches_data(cls, source) -> bool:
        """Return True if the class can handle the data in the source.

        Arguments
        ---------
        source : list of `astropy.io.fits.HDUList`
            The FITS file to be read.

        Returns
        -------
        bool
            True if the class can handle the data in the source.

        Note
        ----
        Typically, this method is implemented by the static method
        `Astrodata._matches_data` or by a class method with the same signature
        for subclasses.

        If you are implementing a subclass, you should override _matches_data
        instead, which is a static method that takes a single argument, the
        source data, and returns a boolean.

        If that method is not overridden, this method will call it with the
        source data as argument.

        For more information, see the documentation for the
        :py:meth:`~AstroData._matches_data` and the |DeveloperGuide|.
        """
        return cls._matches_data(source)

    @staticmethod
    def _matches_data(source):
        """Return True if the source matches conditions for this class.

        .. warning::

            The default implementation for the base |AstroData| class is a
            trivial match (always return True).

        Example
        -------

        .. code-block:: python

            class MyAstroData(AstroData):
                @staticmethod
                def _matches_data(source):
                    if source[0].header["INSTRUME"] == "MY_INST":
                        return True

                    return False

        """
        # This one is trivial. Will be more specific for subclasses.
        logging.debug("Using default _matches_data with %s", source)
        return True

    @property
    def path(self):
        """Return the file path, if generated from or saved to a file.

        If this is set to a file path, the filename will be updated
        automatically. The original filename will be stored in the
        `orig_filename` property.
        """
        return self._path

    @path.setter
    def path(self, value):
        if self._path is None and value is not None:
            self._orig_filename = os.path.basename(value)
        self._path = value

    @property
    def filename(self):
        """Return the filename. This is the basename of the path, or None.

        If the filename is set, the path will be updated automatically.

        If the filename is set to an absolute path, a ValueError will be
        raised.
        """
        if self.path is not None:
            return os.path.basename(self.path)

        return self.path

    @filename.setter
    def filename(self, value):
        if os.path.isabs(value):
            raise ValueError("Cannot set the filename to an absolute path!")

        if self.path is None:
            self.path = os.path.abspath(value)

        else:
            dirname = os.path.dirname(self.path)
            self.path = os.path.join(dirname, value)

    @property
    def orig_filename(self):
        """Return the original file name (before it was modified)."""
        return self._orig_filename

    @orig_filename.setter
    def orig_filename(self, value):
        self._orig_filename = value

    @property
    def phu(self):
        """Return the primary header."""
        return self._phu

    @phu.setter
    def phu(self, phu):
        self._phu = phu

    @property
    def hdr(self):
        """Return all headers, as a |fitsheaderc|.

        If this is a single-slice object, the header will be returned as a
        single :py:class:`~astropy.io.fits.Header` object. Otherwise, it will
        be returned as a |fitsheaderc| object.

        .. |fitsheaderc| replace:: :class:`astrodata.fits.FitsHeaderCollection`
        """
        if not self.nddata:
            return None

        # TODO(teald): Inconsistent type with is_single special case.
        headers = [nd.meta["header"] for nd in self._nddata]
        return headers[0] if self.is_single else FitsHeaderCollection(headers)

    @property
    @deprecated(
        "Access to headers through this property is deprecated and "
        "will be removed in the future. Use '.hdr' instead."
    )
    def header(self):
        """Return the headers for the PHU and each extension.

        .. warning::

            This property is deprecated and will be removed in the future.
        """
        return [self.phu] + [ndd.meta["header"] for ndd in self._nddata]

    @property
    def tags(self):
        """Return a set of strings that represent the class' tags.

        It collects the tags from the methods decorated with the
        :py:func:`~astrodata.astro_data_tag` decorator.
        """
        return self._process_tags()

    @property
    def descriptors(self):
        """Return a sequence of names for descriptor methods.

        These are the methods that are decorated with the
        :py:func:`~astrodata.astro_data_descriptor` decorator.

        This checks for the existence of the descriptor_method attribute in
        the class members, so anything with that attribute (regardless of the
        attribute's value) will be interpreted as a descriptor.

        Returns
        -------
        tuple of str
        """
        members = inspect.getmembers(
            self.__class__, lambda x: hasattr(x, "descriptor_method")
        )
        return tuple(mname for (mname, method) in members)

    @property
    def id(self):
        """Return the extension identifier.

        The identifier is a 1-based extension number for objects with single
        slices.

        For objects that are not single slices, a ValueError will be raised.

        Notes
        -----
        To get all the id values, use the `indices` property and add 1 to each
        value:

        .. code-block:: python

            ids = [i + 1 for i in ad.indices]
        """
        if self.is_single:
            return self._indices[0] + 1

        raise ValueError(
            "Cannot return id for an AstroData object "
            "that is not a single slice"
        )

    @property
    def indices(self):
        """Return the extensions indices for sliced objects."""
        return self._indices if self._indices else list(range(len(self)))

    @property
    def is_sliced(self):
        """Return True if this object is a slice of a dataset.

        If this data provider instance represents a whole dataset, return
        False. If it represents a slice out of a whole, return True.

        It does this by checking if the ``_indices`` private attribute is set.
        """
        return self._indices is not None

    def is_settable(self, attr):
        """Return True if the attribute is meant to be modified."""
        if self.is_sliced and attr in {"path", "filename"}:
            return False

        return attr in self._fixed_settable or attr.isupper()

    @property
    def _nddata(self):
        """Return the list of `astrodata.NDAstroData` objects.

        Unlike ``self.nddata``, this always returns a list.
        """
        if self._indices is not None:
            return [self._all_nddatas[i] for i in self._indices]

        return self._all_nddatas

    @property
    def nddata(self):
        """Return the list of `astrodata.NDAstroData` objects.

        If the `AstroData` object is sliced, this returns only the NDData
        objects of the sliced extensions. And if this is a single extension
        object, the NDData object is returned directly (i.e. not a list).
        """
        return self._nddata[0] if self.is_single else self._nddata

    def table(self):
        """Return a dictionary of `astropy.table.Table` objects.

        Notes
        -----
        This returns a _copy_ of the tables, so modifying them will not
        affect the original ones.
        """
        # FIXME: do we need this in addition to .tables ?
        return self._tables.copy()

    @property
    def tables(self):
        """Return the names of the associated `astropy.table.Table` objects."""
        return set(self._tables)

    @property
    def ext_tables(self):
        """Return names of the extensions' `astropy.table.Table` objects."""
        if not self.is_single:
            raise AttributeError("this is only available for extensions")

        return set(
            key
            for key, obj in self.nddata.meta["other"].items()
            if isinstance(obj, Table)
        )

    @property
    @returns_list
    def shape(self):
        """Return the shape of the data array for each extension.

        Returns
        -------
        list of tuple
        """
        return [nd.shape for nd in self._nddata]

    @property
    @returns_list
    def data(self):
        """Create a list of arrays corresponding to data in extensions.

        This may be a single array, if the data is a single slice.

        If set, it expects the value to be something with a shape, such as a
        numpy array.

        Notes
        -----
        The result will always be a list, even if it's a single slice.
        """
        return [nd.data for nd in self._nddata]

    @data.setter
    @assign_only_single_slice
    def data(self, value):
        # Setting the ._data in the NDData is a bit kludgy, but we're all
        # grown adults and know what we're doing, isn't it?
        if hasattr(value, "shape"):
            self.nddata._data = value

        else:
            raise AttributeError(
                "Trying to assign data to be something with no shape"
            )

    @property
    @returns_list
    def uncertainty(self):
        """Create a list of the uncertainty objects for each extension.

        The objects are instances of AstroPy's `astropy.nddata.NDUncertainty`,
        or `None` where no information is available.

        See Also
        --------
        variance : The actual array supporting the uncertainty object.

        Notes
        -----
        The result will always be a list, even if it's a single slice.
        """
        return [nd.uncertainty for nd in self._nddata]

    @uncertainty.setter
    @assign_only_single_slice
    def uncertainty(self, value):
        self.nddata.uncertainty = value

    @property
    @returns_list
    def mask(self):
        """Return a list of the mask arrays for each extension.

        Returns a list of the mask arrays (or a single array, if this is a
        single slice) attached to the science data, for each extension.

        For objects that miss a mask, `None` will be provided instead.

        Notes
        -----
        The result will always be a list, even if it's a single slice.
        """
        return [nd.mask for nd in self._nddata]

    @mask.setter
    @assign_only_single_slice
    def mask(self, value):
        self.nddata.mask = value

    @property
    @returns_list
    def variance(self):
        """Return a list of variance arrays for each extension.

        A list of the variance arrays (or a single array, if this is a
        single slice) attached to the science data, for each extension.

        For objects that miss uncertainty information, `None` will be provided
        instead.

        See Also
        --------
        uncertainty : The uncertainty objects used under the hood.

        Notes
        -----
        The result will always be a list, even if it's a single slice.
        """
        return [nd.variance for nd in self._nddata]

    @variance.setter
    @assign_only_single_slice
    def variance(self, value):
        if value is None:
            self.nddata.uncertainty = value

        else:
            self.nddata.uncertainty = ADVarianceUncertainty(value)

    @property
    def wcs(self):
        """Return the list of WCS objects for each extension.

        Warning
        -------
        This is what is returned by the ``astropy.nddata.NDData.wcs`` property.
        """
        if self.is_single:
            return self.nddata.wcs

        raise ValueError(
            "Cannot return WCS for an AstroData object "
            "that is not a single slice"
        )

    @wcs.setter
    @assign_only_single_slice
    def wcs(self, value):
        self.nddata.wcs = value

    def __iter__(self):
        """Iterate over the extensions..

        This generator yields the `AstroData` object for each extension.

        Notes
        -----
        This will yield the object, once, if it's a single slice.
        """
        if self.is_single:
            yield self
        else:
            for n in range(len(self)):
                yield self[n]

    def __getitem__(self, idx):
        """Get the item at the specified index.

        Returns a sliced view of the instance. It supports the standard Python
        indexing syntax.

        Arguments
        ---------
        slice : int, `slice`
            An integer or an instance of a Python standard `slice` object

        Raises
        ------
        TypeError
            If trying to slice an object when it doesn't make sense (e.g.
            slicing a single slice)

        ValueError
            If `slice` does not belong to one of the recognized types

        IndexError
            If an index is out of range
        """
        if self.is_single:
            raise TypeError("Can't slice a single slice!")

        indices, _ = normalize_indices(idx, nitems=len(self))

        if self._indices:
            indices = [self._indices[i] for i in indices]

        is_single = not isinstance(idx, (tuple, slice))

        obj = self.__class__(
            self._all_nddatas,
            tables=self._tables,
            phu=self.phu,
            indices=indices,
            is_single=is_single,
        )

        obj._path = self.path
        obj._orig_filename = self.orig_filename

        return obj

    def __delitem__(self, idx):
        """Delete an item using ``del self[idx]``.

        Supports standard Python syntax (including negative indices).

        Arguments
        ---------
        idx : int
            This index represents the order of the element that you want
            to remove.

        Raises
        ------
        IndexError
            If `idx` is out of range.
        """
        if self.is_sliced:
            raise TypeError("Can't remove items from a sliced object")

        del self._all_nddatas[idx]

    def __getattr__(self, attribute):
        """Get the attribute with the specified name.

        Called when an attribute lookup has not found the attribute in the
        usual places (not an instance attribute, and not in the class tree for
        ``self``).

        Arguments
        ---------
        attribute : str
            The attribute's name.

        Raises
        ------
        AttributeError
            If the attribute could not be found/computed.

        Notes
        -----
        For more information, see the documentation on the `__getattr__` method
        in the Python documentation.
        """
        # If we're working with single slices, let's look some things up
        # in the ND object
        if self.is_single and attribute.isupper():
            with suppress(KeyError):
                return self.nddata.meta["other"][attribute]

        if attribute in self._tables:
            return self._tables[attribute]

        raise AttributeError(
            f"{self.__class__.__name__!r} object has no "
            f"attribute {attribute!r}"
        )

    def __setattr__(self, attribute, value):
        """Set the attribute with the specified name to a given value.

        Called when an attribute assignment is attempted, instead of the
        normal mechanism.

        Arguments
        ---------
        attribute : str
            The attribute's name.

        value : object
            The value to be assigned to the attribute.
        """

        def _my_attribute(attr):
            return attr in self.__dict__ or attr in self.__class__.__dict__

        if (
            attribute.isupper()
            and self.is_settable(attribute)
            and not _my_attribute(attribute)
        ):
            # This method is meant to let the user set certain attributes of
            # the NDData objects. First we check if the attribute belongs to
            # this object's dictionary.  Otherwise, see if we can pass it down.
            #
            if self.is_sliced and not self.is_single:
                raise TypeError(
                    "This attribute can only be "
                    "assigned to a single-slice object"
                )

            if attribute == DEFAULT_EXTENSION:
                raise AttributeError(
                    f"{attribute} extensions should be "
                    "appended with .append"
                )

            if attribute in {"DQ", "VAR"}:
                raise AttributeError(
                    f"{attribute} should be set on the " "nddata object"
                )

            add_to = self.nddata if self.is_single else None
            self._append(value, name=attribute, add_to=add_to)

            return

        super().__setattr__(attribute, value)

    def __delattr__(self, attribute):
        """Delete an attribute."""
        if not attribute.isupper():
            super().__delattr__(attribute)
            return

        if self.is_sliced:
            if not self.is_single:
                raise TypeError("Can't delete attributes on non-single slices")

            other = self.nddata.meta["other"]
            if attribute in other:
                del other[attribute]
            else:
                raise AttributeError(
                    f"{self.__class__.__name__!r} sliced "
                    "object has no attribute {attribute!r}"
                )
        else:
            if attribute in self._tables:
                del self._tables[attribute]
            else:
                raise AttributeError(
                    f"'{attribute}' is not a global table " "for this instance"
                )

    def __contains__(self, attribute):
        """Return True if the attribute is exposed in this instance.

        Implements the ability to use the ``in`` operator with an `AstroData`
        object.

        This looks for the attribute in
        :py:meth:``~astrodata.AstroData.exposed``.

        Arguments
        --------
        attribute : str
            An attribute name.

        Returns
        -------
        bool
        """
        return attribute in self.exposed

    def __len__(self):
        """Return the number of independent extensions stored by the object."""
        if self._indices is not None:
            return len(self._indices)

        if self.is_single:
            return 1

        return len(self._all_nddatas)

    @property
    def exposed(self):
        """Return a set of attribute names that can be accessed directly.

        A collection of strings with the names of objects that can be
        accessed directly by name as attributes of this instance, and that are
        not part of its standard interface (i.e. data objects that have been
        added dynamically).

        Examples
        --------
        >>> ad[0].exposed  # doctest: +SKIP
        set(['OBJMASK', 'OBJCAT'])

        """
        exposed = set(self._tables)
        if self.is_single:
            exposed |= set(self.nddata.meta["other"])

        return exposed

    def _pixel_info(self):
        """Get the pixel information for each extension.

        This is a generator that yields a dictionary with the information
        about a single extension, until all extensions have been yielded.

        Yields
        ------
        dict
            A dictionary with the pixel information for an extension.
        """
        for idx, nd in enumerate(self._nddata):
            other_objects = []
            uncer = nd.uncertainty
            fixed = (
                ("variance", None if uncer is None else uncer),
                ("mask", nd.mask),
            )

            for name, other in fixed + tuple(sorted(nd.meta["other"].items())):
                if other is None:
                    continue

                if isinstance(other, Table):
                    other_objects.append(
                        {
                            "attr": name,
                            "type": "Table",
                            "dim": str((len(other), len(other.columns))),
                            "data_type": "n/a",
                        }
                    )

                else:
                    dim = ""
                    if hasattr(other, "dtype"):
                        dt = other.dtype.name
                        dim = str(other.shape)

                    elif hasattr(other, "data"):
                        dt = other.data.dtype.name
                        dim = str(other.data.shape)

                    elif hasattr(other, "array"):
                        dt = other.array.dtype.name
                        dim = str(other.array.shape)

                    else:
                        dt = "unknown"

                    obj_dict = {
                        "attr": name,
                        "type": type(other).__name__,
                        "dim": dim,
                        "data_type": dt,
                    }

                    other_objects.append(obj_dict)

            main_dict = {
                "content": "science",
                "type": type(nd).__name__,
                "dim": str(nd.data.shape),
                "data_type": nd.data.dtype.name,
            }

            out_dict = {
                "idx": f"[{idx:2}]",
                "main": main_dict,
                "other": other_objects,
            }

            yield out_dict

    def info(self):
        """Print out information about the contents of this instance."""
        unknown_file = "Unknown"
        print(f"Filename: {self.path if self.path else unknown_file}")

        # Tags with proper indent and wrapping.
        text = "Tags: " + " ".join(sorted(self.tags))
        textwrapper = textwrap.TextWrapper(width=80, subsequent_indent="    ")

        for line in textwrapper.wrap(text):
            print(line)

        # Data information
        if len(self) > 0:
            main_fmt = "{:6} {:24} {:17} {:14} {}"
            other_fmt = "          .{:20} {:17} {:14} {}"
            print("\nPixels Extensions")
            print(
                main_fmt.format(
                    "Index", "Content", "Type", "Dimensions", "Format"
                )
            )
            for pi in self._pixel_info():
                main_obj = pi["main"]
                print(
                    main_fmt.format(
                        pi["idx"],
                        main_obj["content"][:24],
                        main_obj["type"][:17],
                        main_obj["dim"],
                        main_obj["data_type"],
                    )
                )

                for other in pi["other"]:
                    print(
                        other_fmt.format(
                            other["attr"][:20],
                            other["type"][:17],
                            other["dim"],
                            other["data_type"],
                        )
                    )

        # NOTE: This covers tables, only. Study other cases before
        # implementing a more general solution
        if self._tables:
            print("\nOther Extensions")
            print("               Type        Dimensions")
            for name, table in sorted(self._tables.items()):
                if isinstance(table, list):
                    # This is not a free floating table
                    continue

                print(
                    f".{name[:13]:13s} {'Table':11s} "
                    f"{len(table), len(table.columns)}"
                )

    def _oper(self, operator, operand):
        """Perform an operation on the data with the specified operand."""
        ind = self.indices
        ndd = self._all_nddatas
        if isinstance(operand, AstroData):
            if len(operand) != len(self):
                raise ValueError("Operands are not the same size")

            for n in range(len(self)):
                try:
                    data = (
                        operand.nddata
                        if operand.is_single
                        else operand.nddata[n]
                    )

                    ndd[ind[n]] = operator(ndd[ind[n]], data)

                except TypeError:
                    # This may happen if operand is a sliced, single
                    # AstroData object
                    ndd[ind[n]] = operator(ndd[ind[n]], operand.nddata)

            op_table = operand.table()
            ltab, rtab = set(self._tables), set(op_table)
            for tab in rtab - ltab:
                self._tables[tab] = op_table[tab]

        else:
            for n in range(len(self)):
                ndd[ind[n]] = operator(ndd[ind[n]], operand)

    def _standard_nddata_op(self, fn, operand):
        """Operate on the data with the specified function and operand."""
        return self._oper(
            partial(fn, handle_mask=np.bitwise_or, handle_meta="first_found"),
            operand,
        )

    @format_doc(_ARIT_DOC, name="addition", op="+")
    def __add__(self, oper):  # noqa
        copy = deepcopy(self)
        copy += oper
        return copy

    @format_doc(_ARIT_DOC, name="subtraction", op="-")
    def __sub__(self, oper):  # noqa
        copy = deepcopy(self)
        copy -= oper
        return copy

    @format_doc(_ARIT_DOC, name="multiplication", op="*")
    def __mul__(self, oper):  # noqa
        copy = deepcopy(self)
        copy *= oper
        return copy

    @format_doc(_ARIT_DOC, name="division", op="/")
    def __truediv__(self, oper):  # noqa
        copy = deepcopy(self)
        copy /= oper
        return copy

    @format_doc(_ARIT_DOC, name="inplace addition", op="+=")
    def __iadd__(self, oper):  # noqa
        self._standard_nddata_op(NDAstroData.add, oper)
        return self

    @format_doc(_ARIT_DOC, name="inplace subtraction", op="-=")
    def __isub__(self, oper):  # noqa
        self._standard_nddata_op(NDAstroData.subtract, oper)
        return self

    @format_doc(_ARIT_DOC, name="inplace multiplication", op="*=")
    def __imul__(self, oper):  # noqa
        self._standard_nddata_op(NDAstroData.multiply, oper)
        return self

    @format_doc(_ARIT_DOC, name="inplace division", op="/=")
    def __itruediv__(self, oper):  # noqa
        self._standard_nddata_op(NDAstroData.divide, oper)
        return self

    add = __iadd__
    subtract = __isub__
    multiply = __imul__
    divide = __itruediv__

    __radd__ = __add__
    __rmul__ = __mul__

    def __rsub__(self, oper):
        """Subtract with the operand on the right, using a copy."""
        copy = (deepcopy(self) - oper) * -1
        return copy

    def _rdiv(self, ndd, operand):
        """Divide the data by the NDData object."""
        # Divide method works with the operand first
        return NDAstroData.divide(operand, ndd)

    def __rtruediv__(self, oper):
        """Divide (//) with the operand on the right, using a copy."""
        obj = deepcopy(self)
        obj._oper(obj._rdiv, oper)
        return obj

    def _process_pixel_plane(
        self, pixim, name=None, top_level=False, custom_header=None
    ):
        """Process a pixel plane and return an NDData object.

        Arguments
        ---------
        pixim : `astropy.io.fits.ImageHDU` or `numpy.ndarray`
            The pixel plane to be processed.

        name : str
            The name of the extension.

        top_level : bool
            Whether this is a top-level extension.

        custom_header : `astropy.io.fits.Header`
            A custom header to be used.

        Returns
        -------
        `astrodata.NDAstroData`
            The processed pixel plane.
        """
        # Assume that we get an ImageHDU or something that can be
        # turned into one
        if isinstance(pixim, fits.ImageHDU):
            nd = NDAstroData(pixim.data, meta={"header": pixim.header})
        elif isinstance(pixim, NDAstroData):
            nd = pixim
        else:
            nd = NDAstroData(pixim)

        if custom_header is not None:
            nd.meta["header"] = custom_header

        header = nd.meta.setdefault("header", fits.Header())
        currname = header.get("EXTNAME")

        if currname is None:
            header["EXTNAME"] = name if name is not None else DEFAULT_EXTENSION

        if top_level:
            nd.meta.setdefault("other", OrderedDict())

        return nd

    def _append_array(self, data, name=None, header=None, add_to=None):
        """Append an array to the AstroData object.

        Arguments
        ---------
        data : `numpy.ndarray`
            The data to be appended.

        name : str
            The name of the extension.

        header : `astropy.io.fits.Header`
            The header to be used.

        add_to : `NDAstroData`
            The NDData object to append to.

        Returns
        -------
        `NDAstroData`
            The NDData object that was appended.
        """
        if name in {"DQ", "VAR"}:
            raise ValueError(
                f"'{name}' need to be associated to a "
                f"'{DEFAULT_EXTENSION}' one"
            )

        if add_to is None:
            # Top level extension
            if name is not None:
                hname = name
            elif header is not None:
                hname = header.get("EXTNAME", DEFAULT_EXTENSION)
            else:
                hname = DEFAULT_EXTENSION

            hdu = fits.ImageHDU(data, header=header)
            hdu.header["EXTNAME"] = hname
            ret = self._append_imagehdu(
                hdu, name=hname, header=None, add_to=None
            )
        else:
            ret = add_to.meta["other"][name] = data

        return ret

    def _append_imagehdu(self, hdu, name, header, add_to):
        """Append an ImageHDU to the AstroData object.

        Arguments
        ---------
        hdu : `astropy.io.fits.ImageHDU`
            The ImageHDU to be appended.

        name : str
            The name of the extension.

        header : `astropy.io.fits.Header`
            The header to be used.

        add_to : `NDAstroData`
            The NDData object to append to.

        Returns
        -------
        `NDAstroData`
            The NDData object that was appended.
        """
        if name in {"DQ", "VAR"} or add_to is not None:
            return self._append_array(hdu.data, name=name, add_to=add_to)

        nd = self._process_pixel_plane(
            hdu, name=name, top_level=True, custom_header=header
        )
        return self._append_nddata(nd, name, add_to=None)

    def _append_raw_nddata(self, raw_nddata, name, header, add_to):
        """Append an NDData object to the AstroData object.

        Arguments
        ---------
        raw_nddata : `astropy.nddata.NDData`
            The NDData object to be appended.

        name : str
            The name of the extension.

        header : `astropy.io.fits.Header`
            The header to be used.

        add_to : `NDAstroData`
            The NDData object to append to.

        Returns
        -------
        `NDAstroData`
            The NDData object that was appended.
        """
        logging.debug("Appending data to nddata: %s", name)

        # We want to make sure that the instance we add is whatever we specify
        # as NDDataObject, instead of the random one that the user may pass
        top_level = add_to is None

        if not isinstance(raw_nddata, NDAstroData):
            raw_nddata = NDAstroData(raw_nddata)

        processed_nddata = self._process_pixel_plane(
            raw_nddata, top_level=top_level, custom_header=header
        )
        return self._append_nddata(processed_nddata, name=name, add_to=add_to)

    def _append_nddata(self, new_nddata, name, add_to):
        """Append an NDData object to the AstroData object.

        .. warning::

            This method is only used by others that have constructed NDData
            according to our internal format. We don't accept new headers at
            this point, and that's why it's missing from the signature.  'name'
            is ignored. It's there just to comply with the _append_XXX
            signature.

        Arguments
        ---------
        new_nddata : `NDAstroData`
            The NDData object to be appended.

        name : str
            The name of the extension.

        add_to : `NDAstroData`
            The NDData object to append to.

        Returns
        -------
        `NDAstroData`
            The NDData object that was appended.
        """
        if add_to is not None:
            raise TypeError(
                "You can only append NDData derived instances "
                "at the top level"
            )

        hd = new_nddata.meta["header"]
        hname = hd.get("EXTNAME", DEFAULT_EXTENSION)

        if hname == DEFAULT_EXTENSION:
            self._all_nddatas.append(new_nddata)

        else:
            raise ValueError(
                f"Arbitrary image extensions can only be added "
                f"in association to a '{DEFAULT_EXTENSION}'"
            )

        logging.debug("Appending data to nddata: %s", name)

        return new_nddata

    def _append_table(self, new_table, name, header, add_to):
        """Append a Table object to the AstroData object.

        Arguments
        ---------
        new_table : `astropy.table.Table`
            The Table object to be appended.

        name : str
            The name of the extension.

        header : `astropy.io.fits.Header`
            The header to be used.

        add_to : `NDAstroData`
            The NDData object to append to.

        Returns
        -------
        `NDAstroData`
            The NDData object that was appended.
        """
        tb = _process_table(new_table, name, header)
        hname = tb.meta["header"].get("EXTNAME")

        def find_next_num(tables):
            table_num = 1
            while f"TABLE{table_num}" in tables:
                table_num += 1
            return f"TABLE{table_num}"

        if add_to is None:
            # Find table names for all extensions
            ext_tables = set()
            for nd in self._nddata:
                ext_tables |= set(
                    key
                    for key, obj in nd.meta["other"].items()
                    if isinstance(obj, Table)
                )

            if hname is None:
                hname = find_next_num(set(self._tables) | ext_tables)
            elif hname in ext_tables:
                raise ValueError(
                    f"Cannot append table '{hname}' because it "
                    "would hide an extension table"
                )

            self._tables[hname] = tb
        else:
            if hname in self._tables:
                raise ValueError(
                    f"Cannot append table '{hname}' because it "
                    "would hide a top-level table"
                )

            add_to.meta["other"][hname] = tb

        return tb

    def _append_astrodata(self, ad, name, header, add_to):
        """Append an AstroData object to the AstroData object.

        Arguments
        ---------
        ad : `AstroData`
            The AstroData object to be appended.

        name : str
            The name of the extension.

        header : `astropy.io.fits.Header`
            The header to be used.

        add_to : `NDAstroData`
            The NDData object to append to.

        Returns
        -------
        `NDAstroData`
            The NDData object that was appended.
        """
        logging.debug("Appending astrodata object: %s", name)

        if not ad.is_single:
            raise ValueError(
                "Cannot append AstroData instances that are "
                "not single slices"
            )

        if add_to is not None:
            raise ValueError(
                "Cannot append an AstroData slice to another slice"
            )

        new_nddata = deepcopy(ad.nddata)
        if header is not None:
            new_nddata.meta["header"] = deepcopy(header)

        return self._append_nddata(new_nddata, name=None, add_to=None)

    def _append(self, ext, name=None, header=None, add_to=None):
        """Append an extension to the AstroData object.

        Internal method to dispatch to the type specific methods. This is
        called either by ``.append`` to append on top-level objects only or
        by ``__setattr__``. In the second case ``name`` cannot be None, so
        this is always the case when appending to extensions (add_to != None).
        """
        dispatcher = (
            (NDData, self._append_raw_nddata),
            ((Table, fits.TableHDU, fits.BinTableHDU), self._append_table),
            (fits.ImageHDU, self._append_imagehdu),
            (AstroData, self._append_astrodata),
        )

        for bases, method in dispatcher:
            if isinstance(ext, bases):
                return method(ext, name=name, header=header, add_to=add_to)

        # Assume that this is an array for a pixel plane
        return self._append_array(ext, name=name, header=header, add_to=add_to)

    def append(self, ext, name=None, header=None):
        """Add a new top-level extension.

        Arguments
        ---------
        ext : array, `astropy.nddata.NDData`, `astropy.table.Table`, other
            The contents for the new extension. The exact accepted types depend
            on the class implementing this interface. Implementations specific
            to certain data formats may accept specialized types (eg. a FITS
            provider will accept an `astropy.io.fits.ImageHDU` and extract the
            array out of it).

        name : str, optional
            A name that may be used to access the new object, as an attribute
            of the provider. The name is typically ignored for top-level
            (global) objects, and required for the others. If the name cannot
            be derived from the metadata associated to ``ext``, you will
            have to provider one.
            It can consist in a combination of numbers and letters, with the
            restriction that the letters have to be all capital, and the first
            character cannot be a number ("[A-Z][A-Z0-9]*").

        Returns
        -------
        The same object, or a new one, if it was necessary to convert it to
        a more suitable format for internal use.

        Raises
        ------
        TypeError
            If adding the object in an invalid situation (eg. ``name`` is
            `None` when adding to a single slice).
        ValueError
            Raised if the extension is of a proper type, but its value is
            illegal somehow.

        """
        if self.is_sliced:
            raise TypeError(
                "Can't append objects to slices, use "
                "'ext.NAME = obj' instead"
            )

        # NOTE: Most probably, if we want to copy the input argument, we
        #       should do it here...
        if isinstance(ext, fits.PrimaryHDU):
            raise ValueError(
                "Only one Primary HDU allowed. "
                "Use .phu if you really need to set one"
            )

        if isinstance(ext, Table):
            raise ValueError(
                "Tables should be set directly as attribute, "
                "i.e. 'ad.MYTABLE = table'"
            )

        if name is not None and not name.isupper():
            warnings.warn(
                f"extension name '{name}' should be uppercase", UserWarning
            )
            name = name.upper()

        return self._append(ext, name=name, header=header)

    @classmethod
    def read(cls, source, extname_parser=None):
        """Read from a file, file object, HDUList, etc."""
        return read_fits(cls, source, extname_parser=extname_parser)

    load = read  # for backward compatibility

    def write(self, filename=None, overwrite=False):
        """Write the object to a file.

        Arguments
        ---------
        filename : str, optional
            If the filename is not given, ``self.path`` is used.

        overwrite : bool
            If True, overwrites existing file.

        """
        if filename is None:
            if self.path is None:
                raise ValueError("A filename needs to be specified")
            filename = self.path

        write_fits(self, filename, overwrite=overwrite)

    def operate(self, operator, *args, **kwargs):
        """Apply a function to the data in each extension.

        Applies a function to the main data array on each extension, replacing
        the data with the result. The data will be passed as the first argument
        to the function.

        It will be applied to the mask and variance of each extension, too, if
        they exist.

        This is a convenience method, which is equivalent to::

            for ext in ad:
                ext.data = operator(ext.data, *args, **kwargs)
                if ext.mask is not None:
                    ext.mask = operator(ext.mask, *args, **kwargs)
                if ext.variance is not None:
                    ext.variance = operator(ext.variance, *args, **kwargs)

        with the additional advantage that it will work on single slices, too.

        Arguments
        ---------
        operator : callable
            A function that takes an array (and, maybe, other arguments)
            and returns an array.

        args, kwargs : optional
            Additional arguments to be passed to the ``operator``.

        Examples
        --------
        >>> import numpy as np
        >>> ad.operate(np.squeeze)  # doctest: +SKIP

        """
        # Ensure we can iterate, even on a single slice
        for ext in [self] if self.is_single else self:
            ext.data = operator(ext.data, *args, **kwargs)
            if ext.mask is not None:
                ext.mask = operator(ext.mask, *args, **kwargs)
            if ext.variance is not None:
                ext.variance = operator(ext.variance, *args, **kwargs)

    def reset(self, data, mask=NO_DEFAULT, variance=NO_DEFAULT, check=True):
        """Reset the data, and optionally mask and variance of an extension.

        Sets the ``.data``, and optionally ``.mask`` and ``.variance``
        attributes of a single-extension AstroData slice. This function will
        optionally check whether these attributes have the same shape.

        Arguments
        ---------
        data : ndarray
            The array to assign to the ``.data`` attribute ("SCI").

        mask : ndarray, optional
            The array to assign to the ``.mask`` attribute ("DQ").

        variance: ndarray, optional
            The array to assign to the ``.variance`` attribute ("VAR").

        check: bool
            If set, then the function will check that the mask and variance
            arrays have the same shape as the data array.

        Raises
        ------
        TypeError
            if an attempt is made to set the .mask or .variance attributes
            with something other than an array

        ValueError
            if the .mask or .variance attributes don't have the same shape as
            .data, OR if this is called on an AD instance that isn't a single
            extension slice

        """
        if not self.is_single:
            raise ValueError("Trying to reset a non-sliced AstroData object")

        # In case data is an NDData object
        try:
            self.data = data.data
        except AttributeError:
            self.data = data
        # Set mask, with checking if required
        try:
            if mask.shape != self.data.shape and check:
                raise ValueError("Mask shape incompatible with data shape")

        except AttributeError as err:
            if mask is None:
                self.mask = mask

            elif mask == NO_DEFAULT:
                if hasattr(data, "mask"):
                    self.mask = data.mask

            else:
                raise TypeError("Attempt to set mask inappropriately") from err

        else:
            self.mask = mask

        # Set variance, with checking if required
        try:
            if variance.shape != self.data.shape and check:
                raise ValueError("Variance shape incompatible with data shape")

        except AttributeError as err:
            if variance is None:
                self.uncertainty = None

            elif variance == NO_DEFAULT:
                if hasattr(data, "uncertainty"):
                    self.uncertainty = data.uncertainty

            else:
                raise TypeError(
                    "Attempt to set variance inappropriately"
                ) from err

        else:
            self.variance = variance

        if hasattr(data, "wcs"):
            self.wcs = data.wcs

    def update_filename(self, prefix=None, suffix=None, strip=False):
        """Update the "filename" attribute of the AstroData object.

        A prefix and/or suffix can be specified. If ``strip=True``, these will
        replace the existing prefix/suffix; if ``strip=False``, they will
        simply be prepended/appended.

        The current filename is broken down into its existing prefix, root, and
        suffix using the ``ORIGNAME`` phu keyword, if it exists and is
        contained within the current filename. Otherwise, the filename is split
        at the last underscore and the part before is assigned as the root and
        the underscore and part after the suffix. No prefix is assigned.

        Note that, if ``strip=True``, a prefix or suffix will only be stripped
        if '' is specified.

        Arguments
        ---------
        prefix: str, optional
            New prefix (None => leave alone)

        suffix: str, optional
            New suffix (None => leave alone)

        strip: bool, optional
            Strip existing prefixes and suffixes if new ones are given?

        Raises
        ------
        ValueError
            If the filename cannot be determined
        """
        if self.filename is None:
            if "ORIGNAME" in self.phu:
                self.filename = self.phu["ORIGNAME"]
            else:
                raise ValueError(
                    "A filename needs to be set before it can be updated"
                )

        # Set the ORIGNAME keyword if it's not there
        if "ORIGNAME" not in self.phu:
            self.phu.set(
                "ORIGNAME",
                self.orig_filename,
                "Original filename prior to processing",
            )

        if strip:
            root, filetype = os.path.splitext(self.phu["ORIGNAME"])
            filename, filetype = os.path.splitext(self.filename)
            m = re.match(f"(.*){re.escape(root)}(.*)", filename)

            # Do not strip a prefix/suffix unless a new one is provided
            if m:
                if prefix is None:
                    prefix = m.groups()[0]

                existing_suffix = m.groups()[1]

                if "_" in existing_suffix:
                    last_underscore = existing_suffix.rfind("_")
                    root += existing_suffix[:last_underscore]
                    existing_suffix = existing_suffix[last_underscore:]

            else:
                try:
                    root, existing_suffix = filename.rsplit("_", 1)
                    existing_suffix = "_" + existing_suffix

                except ValueError as err:
                    logging.info(
                        "Could not split filename (ValueError): %s", err
                    )
                    root, existing_suffix = filename, ""

            if suffix is None:
                suffix = existing_suffix

        else:
            root, filetype = os.path.splitext(self.filename)

        # Cope with prefix or suffix as None
        self.filename = (prefix or "") + root + (suffix or "") + filetype

    def _crop_nd(self, nd, x1, y1, x2, y2):
        """Crop the input nd array and its associated attributes.

        Arguments
        ---------
        nd: `NDAstroData`
            The input nd array.
        x1, y1, x2, y2: int
            The minimum (1) and maximum (2) indices for the x and y axis.
        """
        y_start, y_end = y1, y2 + 1
        x_start, x_end = x1, x2 + 1

        nd.data = nd.data[y_start:y_end, x_start:x_end]

        if nd.uncertainty is not None:
            nd.uncertainty = nd.uncertainty[y_start:y_end, x_start:x_end]

        if nd.mask is not None:
            nd.mask = nd.mask[y_start:y_end, x_start:x_end]

    def crop(self, x1, y1, x2, y2):
        """Crop the NDData objects given indices.

        Arguments
        ---------
        x1, y1, x2, y2 : int
            Minimum and maximum indices for the x and y axis.
        """
        for nd in self._nddata:
            orig_shape = nd.data.shape
            self._crop_nd(nd, x1, y1, x2, y2)

            for o in nd.meta["other"].values():
                try:
                    if o.shape == orig_shape:
                        self._crop_nd(o, x1, y1, x2, y2)

                except AttributeError as err:
                    # No 'shape' attribute in the object. It's probably
                    # not array-like
                    err_str = f"{err.__class__.__name__}: {err}"
                    logging.info(f"Could not crop object {o}: {err_str}")
                    pass

    @astro_data_descriptor
    def instrument(self):
        """Return the name of the instrument making the observation."""
        return self.phu.get(self._keyword_for("instrument"))

    @astro_data_descriptor
    def object(self):
        """Return the name of the object being observed."""
        return self.phu.get(self._keyword_for("object"))

    @astro_data_descriptor
    def telescope(self):
        """Return the name of the telescope."""
        return self.phu.get(self._keyword_for("telescope"))

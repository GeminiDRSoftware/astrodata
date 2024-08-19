"""Utility functions and classes for AstroData objects."""

import inspect
import logging
import warnings
from collections import namedtuple
from functools import wraps
from traceback import format_stack

import numpy as np

INTEGER_TYPES = (int, np.integer)

__all__ = (
    "assign_only_single_slice",
    "astro_data_descriptor",
    "AstroDataDeprecationWarning",
    "astro_data_tag",
    "deprecated",
    "normalize_indices",
    "returns_list",
    "TagSet",
    "Section",
)


class AstroDataDeprecationWarning(DeprecationWarning):
    """Warning class for deprecated AstroData methods."""


warnings.simplefilter("always", AstroDataDeprecationWarning)


def deprecated(reason):
    """Mark a function as deprecated.

    Arguments
    ---------
    reason : str
        The reason why the function is deprecated

    Returns
    -------
    function
        The decorated function

    Usage
    -----

    >>> @deprecated("Use another function instead")
    ... def my_function():
    ...     pass

    """

    def decorator_wrapper(fn):
        @wraps(fn)
        def wrapper(*args, **kw):
            current_source = "|".join(format_stack(inspect.currentframe()))
            if current_source not in wrapper.seen:
                wrapper.seen.add(current_source)
                warnings.warn(reason, AstroDataDeprecationWarning)
            return fn(*args, **kw)

        wrapper.seen = set()
        return wrapper

    return decorator_wrapper


def normalize_indices(slc, nitems):
    """Normalize a slice or index to a list of indices."""
    multiple = True
    if isinstance(slc, slice):
        start, stop, step = slc.indices(nitems)
        indices = list(range(start, stop, step))
    elif isinstance(slc, INTEGER_TYPES) or (
        isinstance(slc, tuple)
        and all(isinstance(i, INTEGER_TYPES) for i in slc)
    ):
        if isinstance(slc, INTEGER_TYPES):
            slc = (int(slc),)  # slc's type m
            multiple = False

        else:
            multiple = True

        # Normalize negative indices...
        indices = [(x if x >= 0 else nitems + x) for x in slc]

    else:
        raise ValueError(f"Invalid index: {slc}")

    if any(i >= nitems for i in indices):
        raise IndexError("Index out of range")

    return indices, multiple


class TagSet(namedtuple("TagSet", "add remove blocked_by blocks if_present")):
    """A named tuple of sets of tag strings.

    Named tuple that is used by tag methods to return which actions should
    be performed on a tag set.

    All the attributes are optional, and any combination of them can be used,
    allowing to create complex tag structures.  Read the documentation on the
    tag-generating algorithm if you want to better understand the interactions.

    The simplest TagSet, though, tends to just add tags to the global set.

    It can be initialized by position, like any other tuple (the order of the
    arguments is the one in which the attributes are listed below). It can
    also be initialized by name.

    Attributes
    ----------
    add : set of str, optional
        Tags to be added to the global set

    remove : set of str, optional
        Tags to be removed from the global set

    blocked_by : set of str, optional
        Tags that will prevent this TagSet from being applied

    blocks : set of str, optional
        Other TagSets containing these won't be applied

    if_present : set of str, optional
        This TagSet will be applied only *all* of these tags are present

    Examples
    --------
    >>> TagSet()  # doctest: +SKIP
    TagSet(
        add=set(),
        remove=set(),
        blocked_by=set(),
        blocks=set(),
        if_present=set()
    )
    >>> TagSet({'BIAS', 'CAL'})  # doctest: +SKIP
    TagSet(
        add={'BIAS', 'CAL'}, # These tags are added to the global set
        remove=set(),
        blocked_by=set(),
        blocks=set(),
        if_present=set()
    )
    >>> TagSet(remove={'BIAS', 'CAL'}) # doctest: +SKIP
    TagSet(
        add=set(),
        remove={'BIAS', 'CAL'}, # These tags are removed from the global set
        blocked_by=set(),
        blocks=set(),
        if_present=set()
    )


    Notes
    -----
    If arguments are not provided, the default is an empty set.

    These arguments are not applied within the object, instead they are
    used when tags are being applied to an AstroData object.

    """

    def __new__(
        cls,
        add=None,
        remove=None,
        blocked_by=None,
        blocks=None,
        if_present=None,
    ):
        """Instantiate a new TagSet object."""
        return super().__new__(
            cls,
            add or set(),
            remove or set(),
            blocked_by or set(),
            blocks or set(),
            if_present or set(),
        )


def astro_data_descriptor(fn):
    """Mark a class method as an AstroData descriptor.

    Args
    -----
    fn : method
        The method to be decorated

    Returns
    -------
    The tagged method (not a wrapper)

    Warning
    -------

    If used in combination with other decorators, this one *must* be the one on
    the top (i.e., the last one being applied). It doesn't modify the method in
    any other way.

    e.g.,

    .. code-block:: python

            @astro_data_descriptor # This must be above returns_list
            @returns_list
            def my_descriptor_method(self):
                pass

    Notes
    -----
    This decorator is exactly equivalent to:

    .. code-block:: python

        class MyClass:
            def my_descriptor_method(self):
                pass

            my_descriptor_method.descriptor_method = True

    It is used to mark descriptors for collective operations, such as
    listing out the descriptors an |AstroData| object has or applying
    them to a set of extensions. See the documentation for
    :py:meth:`~astrodata.AstroData.descriptors` for an example.
    """
    fn.descriptor_method = True
    return fn


def returns_list(fn):
    """Ensure a function returns a list.

    Decorator to ensure that descriptors returning a list (of one value per
    extension) only returns single values when operating on single slices; and
    vice versa.

    This is a common case, and you can use the decorator to simplify the
    logic of your descriptors.

    Arguments
    ---------
    fn : Callable
        The method to be decorated

    Returns
    -------
    Callable
        A function

    Example
    -------

    .. code-block:: python

        from astrodata import (
            AstroData,
            astro_data_descriptor,
            returns_list,
            NDAstroData
        )

        class MyAstroData(AstroData):
            @astro_data_descriptor
            @returns_list
            def my_descriptor(self):
                return 1

        # Create an instance of the class with slices
        ad = MyAstroData([NDAstroData([1, 2, 3]), NDAstroData([4, 5, 6])])

        # This will print [1, 1] to stdout
        print(ad.my_descriptor())

    """

    @wraps(fn)
    def wrapper(self, *args, **kwargs):
        ret = fn(self, *args, **kwargs)
        if self.is_single:
            if isinstance(ret, list):
                if len(ret) > 1:
                    logging.warning(
                        "Descriptor %s returned a list "
                        "of %s elements when operating on "
                        "a single slice",
                        fn.__name__,
                        len(ret),
                    )

                return ret[0]

            return ret

        if isinstance(ret, list):
            if len(ret) == len(self):
                return ret

            raise IndexError(
                f"Incompatible numbers of extensions and "
                f"elements in {fn.__name__}"
            )

        return [ret] * len(self)

    return wrapper


def assign_only_single_slice(fn):
    """Raise `ValueError` if assigning to a non-single slice."""

    @wraps(fn)
    def wrapper(self, *args, **kwargs):
        if not self.is_single:
            raise ValueError(
                "Trying to assign to an AstroData object that "
                "is not a single slice"
            )
        return fn(self, *args, **kwargs)

    return wrapper


def astro_data_tag(fn):
    """Mark a method as a tag-producing method.

    Args
    -----
    fn : method
        The method to be decorated

    Returns
    -------
    A wrapper function

    Notes
    -----
    Decorator that marks methods of an `AstroData` derived class as part of
    the tag-producing system.

    It wraps the method around a function that will ensure a consistent return
    value: the wrapped method can return any sequence of sequences of strings,
    and they will be converted to a TagSet. If the wrapped method
    returns None, it will be turned into an empty TagSet.

    Example
    -------

    .. code-block:: python

        class MyAstroData(AstroData):
            @astro_data_tag
            def my_tag_method(self):
                # Below are the tags generated by this method based on whether
                # the instrument is GMOS or not.
                if self.phu.get('INSTRUME') == 'GMOS':
                    return {'GMOS'}

                return {'NOT_GMOS'}
    """

    @wraps(fn)
    def wrapper(self):
        try:
            ret = fn(self)
            if ret is not None:
                if not isinstance(ret, TagSet):
                    raise TypeError(
                        f"Tag function {fn.__name__} didn't return a TagSet"
                    )

                return TagSet(*tuple(set(s) for s in ret))

        except KeyError:
            pass

        # Return empty TagSet for the "doesn't apply" case
        return TagSet()

    wrapper.tag_method = True
    return wrapper


class Section(tuple):
    """A class to handle n-dimensional sections."""

    def __new__(cls, *args, **kwargs):
        """Instantiate a new Section object.

        Expects a sequence of pairs of start and end coordinates for each axis.
        This can be passed in order of axis (e.g., x1, x2, y1, y2) or as a
        set of keyword arguments (e.g., x1=0, x2=10, y1=0, y2=10).

        Arguments
        ---------
        x1, x2, y1, y2, ... : int
            The start and end coordinates for each axis. If passed as
            positional arguments, they should be in order of axis. Otherwise,
            they can be passed as keyword arguments, such as:

            .. code-block:: python

                section = Section(x1=0, x2=10, y1=0, y2=10)
        """
        # Ensure that the order of keys is what we want
        axis_names = [x for axis in "xyzuvw" for x in (f"{axis}1", f"{axis}2")]

        _dict = dict(zip(axis_names, args + ("",) * len(kwargs)))

        _dict.update(kwargs)

        if list(_dict.values()).count("") or (len(_dict) % 2):
            raise ValueError("Cannot initialize 'Section' object")

        instance = tuple.__new__(cls, tuple(_dict.values()))
        instance._axis_names = tuple(_dict.keys())

        if not all(np.diff(instance)[::2] > 0):
            raise ValueError(
                "Not all 'Section' end coordinates exceed the "
                "start coordinates"
            )

        return instance

    @property
    def axis_dict(self):
        """Return a dictionary with the axis names as keys."""
        return dict(zip(self._axis_names, self))

    def __getnewargs__(self):
        """Return arguments needed to create an equivalent Section instance."""
        return tuple(self)

    def __getattr__(self, attr):
        """Check for attrs in the axis_dict (axis names)."""
        if attr in self._axis_names:
            return self.axis_dict[attr]

        raise AttributeError(f"No such attribute '{attr}'")

    def __repr__(self):
        """Return a string representation of the Section object."""
        return (
            "Section("
            + ", ".join([f"{k}={self.axis_dict[k]}" for k in self._axis_names])
            + ")"
        )

    @property
    def ndim(self):
        """The number of dimensions in the section."""
        return len(self) // 2

    @staticmethod
    def from_shape(value):
        """Produce a Section object defining a given shape.

        Examples
        --------
        >>> Section.from_shape((10, 10))
        Section(x1=0, x2=10, y1=0, y2=10)
        >>> Section.from_shape((10, 10, 10))
        Section(x1=0, x2=10, y1=0, y2=10, z1=0, z2=10)
        """
        return Section(*[y for x in reversed(value) for y in (0, x)])

    @staticmethod
    def from_string(value):
        """Produce a Section object from a string."""
        return Section(
            *[
                y
                for x in value.strip("[]").split(",")
                for start, end in [x.split(":")]
                for y in (
                    None if start == "" else int(start) - 1,
                    None if end == "" else int(end),
                )
            ]
        )

    @deprecated(
        "Renamed to 'as_iraf_section', this is just an alias for now "
        "and will be removed in a future version."
    )
    def asIRAFsection(self):  # pylint: disable=invalid-name
        """Produce string with '[x1:x2,y1:y2]' 1-indexed and end-inclusive.

        Deprecated, see :py:meth:`~astrodata.Section.as_iraf_section`.
        """
        return self.as_iraf_section()

    def as_iraf_section(self):
        """Produce string with '[x1:x2,y1:y2]' 1-indexed and end-inclusive.

        This is the format used by IRAF for sections.

        For example,
        >>> Section(0, 10, 0, 10).as_iraf_section()
        '[1:10,1:10]'
        """
        return (
            "["
            + ",".join(
                [
                    ":".join(
                        [
                            str(self.axis_dict[axis] + 1),
                            str(self.axis_dict[axis.replace("1", "2")]),
                        ]
                    )
                    for axis in self._axis_names[::2]
                ]
            )
            + "]"
        )

    # TODO(teald): Deprecate and rename Section.asslice.
    def asslice(self, add_dims=0):
        """Return the Section object as a slice/list of slices.

        Higher dimensionality can be achieved with the add_dims parameter.

        Arguments
        ---------

        add_dims : int
            The number of dimensions to add to the slice.
        """
        return (slice(None),) * add_dims + tuple(
            slice(self.axis_dict[axis], self.axis_dict[axis.replace("1", "2")])
            for axis in reversed(self._axis_names[::2])
        )

    def contains(self, section):
        """Return True if the section is entirely within this Section.

        Arguments
        ---------
        section : Section
            The Section to check for containment.

        Returns
        -------
        bool
            True if the Section is entirely within this Section, otherwise
            False.

        Raises
        ------
        ValueError
            If the Sections have different dimensionality.

        Examples
        --------
        >>> Section(0, 10, 0, 10).contains(Section(1, 9, 1, 9))
        True
        >>> Section(0, 10, 0, 10).contains(Section(1, 11, 1, 9))
        False
        >>> Section(0, 10, 0, 10).contains(Section(1, 9, 1, 11))
        False
        >>> Section(0, 10, 0, 10).contains(Section(1, 3, 1, 7))
        True
        >>> Section(0, 10, 0, 10).contains(Section(1, 3, 1, 11))
        False
        """
        if self.ndim != section.ndim:
            raise ValueError("Sections have different dimensionality")

        con1 = all(s2 >= s1 for s1, s2 in zip(self[::2], section[::2]))

        if not con1:
            return False

        con2 = all(s2 <= s1 for s1, s2 in zip(self[1::2], section[1::2]))

        return con1 and con2

    def is_same_size(self, section):
        """Return True if the Sections are the same size, otherwise False.

        Examples
        --------
        >>> Section(0, 10, 0, 10).is_same_size(Section(0, 10, 0, 10))
        True
        >>> Section(0, 10, 0, 10).is_same_size(Section(0, 10, 0, 11))
        False
        """
        return np.array_equal(np.diff(self)[::2], np.diff(section)[::2])

    def overlap(self, section):
        """Return the overlap between two sections, or None if no overlap.

        Determine whether the two sections overlap. If so, the Section common
        to both is returned, otherwise None.

        Examples
        --------
        >>> Section(0, 10, 0, 10).overlap(Section(1, 9, 1, 9))
        Section(x1=1, x2=9, y1=1, y2=9)
        >>> Section(0, 10, 0, 10).overlap(Section(1, 11, 1, 9))
        Section(x1=1, x2=10, y1=1, y2=9)
        >>> Section(0, 10, 0, 10).overlap(Section(1, 9, 1, 11))
        Section(x1=1, x2=9, y1=1, y2=10)
        >>> Section(0, 10, 0, 10).overlap(Section(1, 3, 1, 7))
        Section(x1=1, x2=3, y1=1, y2=7)
        >>> Section(4, 6, 4, 6).overlap(Section(1, 3, 1, 2))
        None

        Raises
        ------
        ValueError
            If the Sections have different dimensionality.

        Notes
        -----
        If sections do not overlap, a warning is logged when None is returned.
        This is to help with debugging, as it is often not an error condition.
        """
        if self.ndim != section.ndim:
            raise ValueError("Sections have different dimensionality")

        mins = [max(s1, s2) for s1, s2 in zip(self[::2], section[::2])]
        maxs = [min(s1, s2) for s1, s2 in zip(self[1::2], section[1::2])]

        try:
            return self.__class__(
                *[v for pair in zip(mins, maxs) for v in pair]
            )

        # TODO(teald): Check overlap explicitly instead of catching ValueError
        except ValueError as err:
            logging.warning(
                "Sections do not overlap, recieved %s: %s",
                err.__class__.__name__,
                err,
            )

            return None

    def shift(self, *shifts):
        """Shift a section in each direction by the specified amount.

        Arguments
        ---------
        shifts : positional arguments
            The amount to shift the section in each direction.

        Returns
        -------
        Section
            The shifted section.

        Raises
        ------
        ValueError
            If the number of shifts is not equal to the number of dimensions.

        Examples
        --------
        >>> Section(0, 10, 0, 10).shift(1, 1)
        Section(x1=1, x2=11, y1=1, y2=11)
        >>> Section(0, 10, 0, 10).shift(1, 1, 1)
        Traceback (most recent call last):
        ...
        ValueError: Number of shifts 3 incompatible with dimensionality 2
        """
        if len(shifts) != self.ndim:
            raise ValueError(
                f"Number of shifts {len(shifts)} incompatible "
                f"with dimensionality {self.ndim}"
            )
        return self.__class__(
            *[
                x + s
                for x, s in zip(self, [ss for s in shifts for ss in [s] * 2])
            ]
        )

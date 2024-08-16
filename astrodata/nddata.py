"""Implementations of NDData-like classes for |AstroData| objects.

This module implements a derivative class based on NDData with some Mixins,
implementing windowing and on-the-fly data scaling.
"""

import warnings
from copy import deepcopy
from functools import reduce

import numpy as np
from astropy.io.fits import ImageHDU
from astropy.modeling import Model, models
from astropy.nddata import (
    NDArithmeticMixin,
    NDData,
    NDSlicingMixin,
    VarianceUncertainty,
)
from gwcs.wcs import WCS as gWCS

from .wcs import remove_axis_from_frame

INTEGER_TYPES = (int, np.integer)

__all__ = ["NDAstroData"]


class ADVarianceUncertainty(VarianceUncertainty):
    """Subclass VarianceUncertainty to check for negative values."""

    @VarianceUncertainty.array.setter
    def array(self, value):
        if value is not None and np.any(value < 0):
            warnings.warn(
                "Negative variance values found. Setting to zero.",
                RuntimeWarning,
            )
            value = np.where(value >= 0.0, value, 0.0)
        VarianceUncertainty.array.fset(self, value)


class AstroDataMixin:
    """Mixin with AstroData-like behavior for NDData-like classes.

    Mixin for ``NDData``-like classes (such as ``Spectrum1D``) to enable
    them to behave similarly to ``AstroData`` objects.

    These behaviors are:
        1.  ``mask`` attributes are combined with bitwise, not logical, or,
            since the individual bits are important.
        2.  The WCS must be a ``gwcs.WCS`` object and slicing results in
            the model being modified.
        3.  There is a settable ``variance`` attribute.
        4.  Additional attributes such as OBJMASK can be extracted from
            the .meta['other'] dict
    """

    def __getattr__(self, attribute):
        """Access attributes stored in self.meta['other'].

        Required to access attributes like |AstroData| objects. See the
        documentation for |AstroData|'s ``__getattr__`` method for more
        information.
        """
        if attribute.isupper():
            try:
                return self.meta["other"][attribute]

            # Does this ever happen? If so under what circumstances?
            except KeyError:
                pass

        raise AttributeError(
            f"{self.__class__.__name__!r} object has no "
            f"attribute {attribute!r}"
        )

    def _arithmetic(
        self,
        operation,
        operand,
        propagate_uncertainties=True,
        handle_mask=np.bitwise_or,
        handle_meta=None,
        uncertainty_correlation=0,
        compare_wcs="first_found",
        **kwds,
    ):
        """Perform arithmetic operations on the data.

        Overrides the NDData method so that "bitwise_or" becomes the default
        operation to combine masks, rather than "logical_or"

        .. warning::
            This method is not intended to be called directly. Use the
            arithmetic methods of the NDData object instead.
        """
        return super()._arithmetic(
            operation,
            operand,
            propagate_uncertainties=propagate_uncertainties,
            handle_mask=handle_mask,
            handle_meta=handle_meta,
            uncertainty_correlation=uncertainty_correlation,
            compare_wcs=compare_wcs,
            **kwds,
        )

    def _slice_wcs(self, slices):
        """Slice the WCS object.

        The ``__call__()`` method of gWCS doesn't appear to conform to the
        APE 14 interface for WCS implementations, and doesn't react to slicing
        properly. We override NDSlicing's method to do what we want.

        Arguments
        ---------
        slices : slice or tuple of slices
            The slice or slices to apply to the WCS.
        """
        if not isinstance(self.wcs, gWCS):
            return self.wcs

        # Sanitize the slices, catching some errors early
        if not isinstance(slices, (tuple, list)):
            slices = (slices,)
        slices = list(slices)
        ndim = len(self.shape)
        if len(slices) > ndim:
            raise ValueError(
                f"Too many dimensions specified in slice {slices}"
            )

        if Ellipsis in slices:
            if slices.count(Ellipsis) > 1:
                raise IndexError(
                    "Only one ellipsis can be specified in a slice"
                )

            ell_index = slices.index(Ellipsis) + 1
            slice_fill = [slice(None)] * (ndim - len(slices) + 1)
            slices[ell_index:ell_index] = slice_fill

        slices.extend([slice(None)] * (ndim - len(slices)))

        mods = []
        mapped_axes = []
        for i, (slice_, length) in enumerate(zip(slices[::-1], self.shape)):
            model = []
            if isinstance(slice_, slice):
                if slice_.step and slice_.step > 1:
                    raise IndexError("Cannot slice with a step")
                if slice_.start:
                    start = (
                        length + slice_.start
                        if slice_.start < 1
                        else slice_.start
                    )
                    if start > 0:
                        model.append(models.Shift(start))
                mapped_axes.append(max(mapped_axes) + 1 if mapped_axes else 0)
            elif isinstance(slice_, INTEGER_TYPES):
                model.append(models.Const1D(slice_))
                mapped_axes.append(-1)
            else:
                raise IndexError("Slice not an integer or range")
            if model:
                mods.append(reduce(Model.__or__, model))
            else:
                # If the previous model was an Identity, we can hang this
                # one onto that without needing to append a new Identity
                if i > 0 and isinstance(mods[-1], models.Identity):
                    mods[-1] = models.Identity(mods[-1].n_inputs + 1)
                else:
                    mods.append(models.Identity(1))

        slicing_model = reduce(Model.__and__, mods)
        if mapped_axes != list(np.arange(ndim)):
            slicing_model = (
                models.Mapping(tuple(max(ax, 0) for ax in mapped_axes))
                | slicing_model
            )
            slicing_model.inverse = models.Mapping(
                tuple(ax for ax in mapped_axes if ax != -1), n_inputs=ndim
            )

        if (
            isinstance(slicing_model, models.Identity)
            and slicing_model.n_inputs == ndim
        ):
            return self.wcs  # Unchanged!
        new_wcs = deepcopy(self.wcs)
        input_frame = new_wcs.input_frame
        for axis, mapped_axis in reversed(list(enumerate(mapped_axes))):
            if mapped_axis == -1:
                input_frame = remove_axis_from_frame(input_frame, axis)
        new_wcs.pipeline[0].frame = input_frame
        new_wcs.insert_transform(
            new_wcs.input_frame, slicing_model, after=True
        )
        return new_wcs

    @property
    def variance(self):
        """Access the contents of ``uncertainty``."""
        return getattr(self.uncertainty, "array", None)

    @variance.setter
    def variance(self, value):
        self.uncertainty = (
            ADVarianceUncertainty(value) if value is not None else None
        )

    @property
    def wcs(self):
        """Return the WCS of the data as a gWCS object.

        This is a gWCS object, not a FITS WCS object.

        This is returning wcs from an inhertited class, see NDData.wcs for more
        details.
        """
        return super().wcs

    @wcs.setter
    def wcs(self, value):
        if value is not None and not isinstance(value, gWCS):
            raise TypeError("wcs value must be None or a gWCS object")
        self._wcs = value

    @property
    def shape(self):
        """The shape of the data."""
        return self._data.shape

    @property
    def size(self):
        """The size of the data."""
        return self._data.size


class FakeArray:
    """Fake array class for lazy-loaded data.

    A class that pretends to be an array, but is actually a lazy-loaded.
    This is used to fool the NDData class into thinking it has an array
    when it doesn't.
    """

    def __init__(self, very_faked):
        self.data = very_faked
        self.shape = (100, 100)  # Won't matter. This is just to fool NDData
        self.dtype = np.float32  # Same here

    def __getitem__(self, index):
        return None

    def __array__(self):
        return self.data


class NDWindowing:
    """Window access to an ``NDAstroData`` instance.

    A class to allow "windowed" access to some properties of an
    ``NDAstroData`` instance. In particular, ``data``, ``uncertainty``,
    ``variance``, and ``mask`` return clipped data.
    """

    def __init__(self, target):
        self._target = target

    def __getitem__(self, window_slice):
        return NDWindowingAstroData(self._target, window=window_slice)


class NDWindowingAstroData(
    AstroDataMixin, NDArithmeticMixin, NDSlicingMixin, NDData
):
    """Implement windowed access to an ``NDAstroData`` instance.

    Provide "windowed" access to some properties of an ``NDAstroData``
    instance.  In particular, ``data``, ``uncertainty``, ``variance``, and
    ``mask`` return clipped data.
    """

    # pylint: disable=super-init-not-called
    def __init__(self, target, window):
        self._target = target
        self._window = window

    def __getattr__(self, attribute):
        """Access attributes stored in self.meta['other'].

        This is required to access attributes like |AstroData| objects. See the
        documentation for |AstroData|'s ``__getattr__`` method for more
        information.
        """
        if attribute.isupper():
            try:
                return self._target._get_simple(
                    attribute, section=self._window
                )
            except KeyError:
                pass
        raise AttributeError(
            f"{self.__class__.__name__!r} object has no "
            f"attribute {attribute!r}"
        )

    @property
    def unit(self):
        return self._target.unit

    @property
    def wcs(self):
        return self._target._slice_wcs(self._window)

    @property
    def data(self):
        return self._target._get_simple("_data", section=self._window)

    @property
    def uncertainty(self):
        return self._target._get_uncertainty(section=self._window)

    @property
    def variance(self):
        if self.uncertainty is not None:
            return self.uncertainty.array

        return None

    @property
    def mask(self):
        return self._target._get_simple("_mask", section=self._window)


def is_lazy(item):
    """Return True if the item is a lazy-loaded object, False otherwise."""
    return isinstance(item, ImageHDU) or getattr(item, "lazy", False)


class NDAstroData(AstroDataMixin, NDArithmeticMixin, NDSlicingMixin, NDData):
    """Primary data class for AstroData objects.

    Implements ``NDData`` with all Mixins, plus some ``AstroData`` specifics.

    This class implements an ``NDData``-like container that supports reading
    and writing as implemented in the ``astropy.io.registry`` and also slicing
    (indexing) and simple arithmetics (add, subtract, divide and multiply).

    A very important difference between ``NDAstroData`` and ``NDData`` is that
    the former attempts to load all its data lazily. There are also some
    important differences in the interface (eg. ``.data`` lets you reset its
    contents after initialization).

    Documentation is provided where our class differs.

    See Also
    --------
    NDData
    NDArithmeticMixin
    NDSlicingMixin

    Examples
    --------
    The mixins allow operation that are not possible with ``NDData`` or
    ``NDDataBase``, i.e. simple arithmetics::

        >>> from astropy.nddata import StdDevUncertainty
        >>> import numpy as np
        >>> data = np.ones((3,3), dtype=float)
        >>> ndd1 = NDAstroData(data, uncertainty=StdDevUncertainty(data))
        >>> ndd2 = NDAstroData(data, uncertainty=StdDevUncertainty(data))
        >>> ndd3 = ndd1.add(ndd2)
        >>> ndd3.data
        array([[2., 2., 2.],
            [2., 2., 2.],
            [2., 2., 2.]])
        >>> ndd3.uncertainty.array
        array([[1.41421356, 1.41421356, 1.41421356],
            [1.41421356, 1.41421356, 1.41421356],
            [1.41421356, 1.41421356, 1.41421356]])

    see ``NDArithmeticMixin`` for a complete list of all supported arithmetic
    operations.

    But also slicing (indexing) is possible::

        >>> ndd4 = ndd3[1,:]
        >>> ndd4.data
        array([2., 2., 2.])
        >>> ndd4.uncertainty.array
        array([1.41421356, 1.41421356, 1.41421356])

    See ``NDSlicingMixin`` for a description how slicing works (which
    attributes) are sliced.
    """

    def __init__(
        self,
        data,
        uncertainty=None,
        mask=None,
        wcs=None,
        meta=None,
        unit=None,
        copy=False,
        variance=None,
    ):
        """Initialize an ``NDAstroData`` instance.

        Arguments
        ---------
        data : array-like
            The actual data. This can be a numpy array, a memmap, or a
            ``fits.ImageHDU`` object.

        uncertainty : ``NDUncertainty``-like object, optional
            An object that represents the uncertainty of the data. If not
            specified, the uncertainty will be set to None.

        mask : array-like, optional
            An array that represents the mask of the data. If not specified,
            the mask will be set to None.

        wcs : ``gwcs.WCS`` object, optional
            The WCS of the data. If not specified, the WCS will be set to None.

        meta : dict-like, optional
            A dictionary-like object that holds the meta data. If not
            specified, the meta data will be set to None.

        unit : ``astropy.units.Unit`` object, optional
            The unit of the data. If not specified, the unit will be set to
            None.

        copy : bool, optional
            If True, the data, uncertainty, mask, wcs, meta, and unit will be
            copied. Otherwise, they will be referenced. Default is False.

        variance : array-like, optional
            An array that represents the variance of the data. If not
            specified, the variance will be set to None.

        Raises
        ------
        ValueError
            If ``uncertainty`` and ``variance`` are both specified.

        Notes
        -----
        The ``uncertainty`` and ``variance`` parameters are mutually exclusive.
        """
        if variance is not None:
            if uncertainty is not None:
                raise ValueError(
                    f"Cannot specify both uncertainty and variance"
                    f"({uncertainty = }, {variance = })."
                )

            uncertainty = ADVarianceUncertainty(variance)

        super().__init__(
            FakeArray(data) if is_lazy(data) else data,
            None if is_lazy(uncertainty) else uncertainty,
            mask,
            wcs,
            meta,
            unit,
            copy,
        )

        if is_lazy(data):
            self.data = data
        if is_lazy(uncertainty):
            self.uncertainty = uncertainty

    def __deepcopy__(self, memo):
        """Implement the deepcopy protocol for this class.

        This implementation accounts for the lazy-loading of the data and
        uncertainty attributes. It also avoids recursion when copying the
        uncertainty attribute.
        """
        new = self.__class__(
            self._data if is_lazy(self._data) else deepcopy(self.data, memo),
            self._uncertainty if is_lazy(self._uncertainty) else None,
            self._mask if is_lazy(self._mask) else deepcopy(self.mask, memo),
            deepcopy(self.wcs, memo),
            None,
            self.unit,
        )
        new.meta = deepcopy(self.meta, memo)
        # Needed to avoid recursion because of uncertainty's weakref to self
        if not is_lazy(self._uncertainty):
            new.variance = deepcopy(self.variance)
        return new

    @property
    def window(self):
        """Access a slice of the data.

        Interface to access a section of the data, using lazy access
        whenever possible.

        Returns
        -------
        An instance of ``NDWindowing``, which provides ``__getitem__``,
        to allow the use of square brackets when specifying the window.
        Ultimately, an ``NDWindowingAstrodata`` instance is returned.

        Examples
        --------
        >>> ad[0].nddata.window[100:200, 100:200]  # doctest: +SKIP
        <NDWindowingAstrodata .....>
        """
        return NDWindowing(self)

    def _get_uncertainty(self, section=None):
        """Return the ADVarianceUncertainty object, or a slice of it.

        Arguments
        ---------
        section : slice, optional
            The slice to apply to the uncertainty object.

        Returns
        -------
        ADVarianceUncertainty
            The uncertainty object, or a slice of it if a section is provided.
        """
        if self._uncertainty is not None:
            if is_lazy(self._uncertainty):
                if section is None:
                    self.uncertainty = ADVarianceUncertainty(
                        self._uncertainty.data
                    )
                    return self.uncertainty

                return ADVarianceUncertainty(self._uncertainty[section])

            if section is not None:
                return self._uncertainty[section]

            return self._uncertainty

        return None

    def _get_simple(self, target, section=None):
        """Return the section of image-like objects, or the whole object.

        Only use 'section' for image-like objects that have the same shape
        as the NDAstroData object; otherwise, return the whole object.
        """
        # TODO(teald): Unclear description of what this method does.
        source = getattr(self, target)
        if source is not None:
            if is_lazy(source):
                if section is None:
                    ret = np.empty(source.shape, dtype=source.dtype)
                    ret[:] = source.data
                    setattr(self, target, ret)

                else:
                    ret = source[section]

                return ret

            if hasattr(source, "shape"):
                if section is None or source.shape != self.shape:
                    return np.array(source, copy=False)

                return np.array(source, copy=False)[section]

            return source

        return None

    @property
    def data(self):
        """Access the data stored in this instance. It implements a setter."""
        return self._get_simple("_data")

    @data.setter
    def data(self, value):
        if value is None:
            raise ValueError(f"Cannot set data to {value}.")

        if is_lazy(value):
            self.meta["header"] = value.header

        self._data = value

    @property
    def uncertainty(self):
        """Get or set the uncertainty of the data."""
        return self._get_uncertainty()

    @uncertainty.setter
    def uncertainty(self, value):
        if value is not None and not is_lazy(value):
            # TODO: Accessing protected member from value
            # pylint: disable=protected-access
            if value._parent_nddata is not None:
                value = value.__class__(value, copy=False)

            value.parent_nddata = self

        self._uncertainty = value

    @property
    def mask(self):
        """Get or set the mask of the data."""
        return self._get_simple("_mask")

    @mask.setter
    def mask(self, value):
        self._mask = value

    @property
    def variance(self):
        """Get and aset the variance of the data.

        A convenience property to access the contents of ``uncertainty``,
        squared (as the uncertainty data is stored as standard deviation).
        """
        # TODO(teald): Refactor uncertainty and variance implementation.
        arr = self._get_uncertainty()

        if arr is not None:
            return arr.array

        return arr

    @variance.setter
    def variance(self, value):
        self.uncertainty = (
            ADVarianceUncertainty(value) if value is not None else None
        )

    def set_section(self, section, input_data):
        """Set a section of the data to the input data.

        Sets only a section of the data. This method is meant to prevent
        fragmentation in the Python heap, by reusing the internal structures
        instead of replacing them with new ones.

        Arguments
        ---------
        section : ``slice``
            The area that will be replaced

        input_data : ``NDData``-like instance
            This object needs to implement at least ``data``, ``uncertainty``,
            and ``mask``. Their entire contents will replace the data in the
            area defined by ``section``.

        Examples
        --------
        >>> def setup():
        ...     sec = NDData(np.zeros((100,100)))
        ...     ad[0].nddata.set_section(
        ...         (slice(None,100),slice(None,100)),
        ...         sec
        ...     )
        ...
        >>> setup()  # doctest: +SKIP

        """
        self.data[section] = input_data.data

        if self.uncertainty is not None:
            self.uncertainty.array[section] = input_data.uncertainty.array

        if self.mask is not None:
            self.mask[section] = input_data.mask

    def __repr__(self):
        """Return a string representation of the object.

        If the data is lazy-loaded, the string representation will include
        the class name and the string "(Memmapped)", representing that this
        memory may not have been loaded in yet.
        """
        # TODO(teald): Check that repr reverts to normal behavior after loading
        if is_lazy(self._data):
            return self.__class__.__name__ + "(Memmapped)"

        return super().__repr__()

    # This is a common idiom in numpy, so keep the name.
    # pylint: disable=invalid-name
    @property
    def T(self):
        """Transpose the data. This is not a copy of the data."""
        return self.transpose()

    def transpose(self):
        """Transpose the data. This is not a copy of the data."""
        unc = self.uncertainty
        new_wcs = deepcopy(self.wcs)
        inframe = new_wcs.input_frame
        new_wcs.insert_transform(
            inframe,
            models.Mapping(tuple(reversed(range(inframe.naxes)))),
            after=True,
        )
        return self.__class__(
            self.data.T,
            uncertainty=None if unc is None else unc.__class__(unc.array.T),
            mask=None if self.mask is None else self.mask.T,
            wcs=new_wcs,
            copy=False,
        )

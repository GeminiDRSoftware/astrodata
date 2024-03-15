# disable pylint for this file
# pylint: disable-all
import warnings

import pytest

from numpy.testing import assert_array_almost_equal, assert_array_equal
import numpy as np

from astrodata import wcs as adwcs
from astrodata.fits import FitsLazyLoadable, windowed_operation
from astrodata.nddata import (
    ADVarianceUncertainty,
    AstroDataMixin,
    FakeArray,
    is_lazy,
    NDAstroData,
)

from astropy.io import fits
from astropy.modeling import models
from astropy.nddata import NDData, VarianceUncertainty
from astropy.table import Table

from gwcs.coordinate_frames import Frame2D
from gwcs.wcs import WCS as gWCS


@pytest.fixture
def testnd():
    shape = (5, 5)
    # hdr = fits.Header({"CRPIX1": 1, "CRPIX2": 2})
    nd = NDAstroData(
        data=np.arange(np.prod(shape)).reshape(shape),
        variance=np.ones(shape) + 0.5,
        mask=np.zeros(shape, dtype=bool),
        wcs=gWCS(
            models.Shift(1) & models.Shift(2),
            input_frame=adwcs.pixel_frame(2),
            output_frame=adwcs.pixel_frame(2, name="world"),
        ),
        unit="ct",
    )
    nd.meta["other"] = {
        "OBJMASK": np.arange(np.prod(shape)).reshape(shape),
        "OBJCAT": Table([[1, 2, 3]], names=[["number"]]),
    }
    nd.mask[3, 4] = True
    return nd


def test_getattr(testnd):
    # Try accessing a good key and a bad key.
    testnd.OBJMASK
    testnd.OBJCAT

    with pytest.raises(AttributeError):
        testnd.bad_attr

    with pytest.raises(AttributeError):
        testnd.BAD_ATTR


def test_var(testnd):
    data = np.zeros(5)
    var = np.array([1.2, 2, 1.5, 1, 1.3])
    nd1 = NDAstroData(data=data, uncertainty=ADVarianceUncertainty(var))
    nd2 = NDAstroData(data=data, variance=var)
    assert_array_equal(nd1.variance, nd2.variance)


def test_window(testnd):
    win = testnd.window[2:4, 3:5]
    assert win.unit == "ct"
    # assert_array_equal(win.wcs.wcs.crpix, [1, 2])
    assert_array_equal(win.data, [[13, 14], [18, 19]])
    assert_array_equal(win.mask, [[False, False], [False, True]])
    assert_array_almost_equal(win.uncertainty.array, 1.5)
    assert_array_almost_equal(win.variance, 1.5)


def test_windowedOp(testnd):
    def stack(arrays):
        arrays = [x for x in arrays]
        data = np.array([arr.data for arr in arrays]).sum(axis=0)
        unc = np.array([arr.uncertainty.array for arr in arrays]).sum(axis=0)
        mask = np.array([arr.mask for arr in arrays]).sum(axis=0)
        return NDAstroData(data=data, variance=unc, mask=mask)

    result = windowed_operation(
        stack,
        [testnd, testnd],
        kernel=(3, 3),
        with_uncertainty=True,
        with_mask=True,
    )
    assert_array_equal(result.data, testnd.data * 2)
    assert_array_equal(result.uncertainty.array, testnd.uncertainty.array * 2)
    assert result.mask[3, 4] == 2

    nd2 = NDAstroData(data=np.zeros((4, 4)))
    with pytest.raises(ValueError, match=r"Can't calculate final shape.*"):
        result = windowed_operation(stack, [testnd, nd2], kernel=(3, 3))

    with pytest.raises(AssertionError, match=r"Incompatible shape.*"):
        result = windowed_operation(
            stack, [testnd, testnd], kernel=[3], shape=(5, 5)
        )


@pytest.mark.skip(
    "This is tested elsewhere, not explicitly. Not entirely "
    "sure exactly what it's doing or where yet."
)
def test_override_arithmatic(testnd):
    # Test whether the _arithmetic override actually works.
    raise NotImplementedError


def test_transpose(testnd):
    testnd.variance[0, -1] = 10
    ndt = testnd.T
    assert_array_equal(ndt.data[0], [0, 5, 10, 15, 20])
    assert ndt.variance[-1, 0] == 10
    assert ndt.wcs(1, 2) == testnd.wcs(2, 1)


def test_set_section(testnd):
    sec = NDData(
        np.zeros((2, 2)), uncertainty=VarianceUncertainty(np.ones((2, 2)))
    )
    testnd.set_section((slice(0, 2), slice(1, 3)), sec)
    assert_array_equal(testnd[:2, 1:3].data, 0)
    assert_array_equal(testnd[:2, 1:3].variance, 1)


def test_uncertainty_negative_numbers():
    arr = np.zeros(5)

    # No warning if all 0
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        ADVarianceUncertainty(arr)

    arr[2] = -0.001

    with pytest.warns(RuntimeWarning, match="Negative variance values found."):
        result = ADVarianceUncertainty(arr)

    assert not np.all(arr >= 0)
    assert isinstance(result, ADVarianceUncertainty)
    assert result.array[2] == 0

    # check that it always works with a VarianceUncertainty instance
    result.array[2] = -0.001

    with pytest.warns(RuntimeWarning, match="Negative variance values found."):
        result2 = ADVarianceUncertainty(result)

    assert not np.all(arr >= 0)
    assert not np.all(result.array >= 0)
    assert isinstance(result2, ADVarianceUncertainty)
    assert result2.array[2] == 0


def test_wcs_slicing():
    nd = NDAstroData(np.zeros((50, 50)))
    in_frame = Frame2D(name="in_frame")
    out_frame = Frame2D(name="out_frame")
    gwcs = gWCS([(in_frame, models.Identity(2)), (out_frame, None)])
    nd.wcs = gwcs
    assert nd.wcs(10, 10) == (10, 10)
    assert nd[10:].wcs(10, 10) == (10, 20)
    assert nd[..., 10:].wcs(10, 10) == (20, 10)
    assert nd[:, 5].wcs(10) == (5, 10)
    assert nd[20, -10:].wcs(0) == (40, 20)

    # Test when two identity models are used
    i_gwcs = gWCS(
        [
            (in_frame, models.Identity(2)),
            (out_frame, models.Identity(2)),
            (in_frame, models.Identity(2)),
        ]
    )

    nd.wcs = i_gwcs

    assert nd.wcs(10, 10) == (10, 10)
    assert nd[10:].wcs(10, 10) == (10, 20)
    assert nd[..., 10:].wcs(10, 10) == (20, 10)
    assert nd[:, 5].wcs(10) == (5, 10)
    assert nd[20, -10:].wcs(0) == (40, 20)

    # Just to ensure it doesn't get referenced later in the test.
    nd.wcs = gwcs
    del i_gwcs

    # Test when wcs is not a gWCS object (none)
    # Error will be caught before it notices this is a bad slice.
    nd.wcs = None
    assert nd._slice_wcs((100, 101)) is None

    # Revert to gwcs
    nd.wcs = gwcs

    # Too many dims
    with pytest.raises(ValueError):
        nd._slice_wcs([(1, 1), (2, 2), (3, 3)])

    # Too many ellipses
    with pytest.raises(IndexError):
        nd._slice_wcs([..., ...])

    # Using a step
    sl = slice(0, 1, 2)
    with pytest.raises(IndexError):
        nd._slice_wcs(sl)

    # Using a bad nonslice (that could be mistaken for a proper slice)
    with pytest.raises(IndexError):
        nd._slice_wcs(lambda: slice(0, 1))


def test_access_to_other_planes(testnd):
    assert hasattr(testnd, "OBJMASK")
    assert testnd.OBJMASK.shape == testnd.data.shape
    assert hasattr(testnd, "OBJCAT")
    assert isinstance(testnd.OBJCAT, Table)
    assert len(testnd.OBJCAT) == 3


def test_access_to_other_planes_when_windowed(testnd):
    ndwindow = testnd.window[1:, 1:]
    assert ndwindow.data.shape == (4, 4)
    assert ndwindow.data[0, 0] == testnd.shape[1] + 1
    assert ndwindow.OBJMASK.shape == (4, 4)
    assert ndwindow.OBJMASK[0, 0] == testnd.shape[1] + 1
    assert isinstance(ndwindow.OBJCAT, Table)
    assert len(ndwindow.OBJCAT) == 3


def test_variance_uncertainty_AstroDataMixin(testnd):
    class TestClass(AstroDataMixin):
        pass

    variance = testnd.uncertainty.array

    testclass_testnd = TestClass()
    testclass_testnd.variance = variance

    print(testclass_testnd.variance, testclass_testnd.uncertainty, sep="\n")

    assert isinstance(testclass_testnd.uncertainty, ADVarianceUncertainty)

    assert_array_equal(
        testclass_testnd.uncertainty.array, testclass_testnd.variance
    )

    # Test setting the variance
    testclass_testnd.variance = 2
    assert_array_equal(testclass_testnd.uncertainty.array, 2)
    assert_array_equal(
        testclass_testnd.variance,
        testclass_testnd.uncertainty.array,
    )

    # Test setting variance to None
    testclass_testnd.variance = None
    assert testclass_testnd.uncertainty is None


def test_FakeArray():
    # This is for completeness
    data = np.empty(100)
    fake = FakeArray(data)

    assert fake[0] is None
    assert fake.__array__() is data


def test_NDWindowingAstroData_bad_key(testnd):
    with pytest.raises(AttributeError):
        testnd.window[0:].BAD_KEY123

    with pytest.raises(AttributeError):
        testnd.window[0:].bad_key123


def test_NDWindowingAstroData_slice(testnd):
    wcs = testnd.window[0:].wcs

    assert wcs(0, 0) == (1, 2)
    assert wcs(1, 1) == (2, 3)
    assert wcs(2, 2) == (3, 4)


def test_no_uncertainty():
    nd = NDAstroData(data=np.zeros((5, 5)))
    assert nd.uncertainty is None
    assert nd.variance is None

    # Test for NDWindowingAstroData
    assert nd.window[1:, 1:].uncertainty is None
    assert nd.window[1:, 1:].variance is None


def test_NDAstroData_specify_variance_and_uncertainty():
    with pytest.raises(ValueError):
        NDAstroData(
            data=np.zeros((5, 5)),
            uncertainty=VarianceUncertainty(np.ones((5, 5))),
            variance=np.ones((5, 5)),
        )


@pytest.mark.skip(reason="Not sure how to test this yet.")
def test_NDAstroData_with_lazy_data():
    data = fits.ImageHDU(
        data=np.array([1, 2, 3]),
        header=fits.Header(cards=[fits.Card("EXTNAME", "bing")]),
    )

    assert is_lazy(data)
    nd = NDAstroData(data=data)

    # Test for NDWindowingAstroData
    assert nd.window[0:, 0:].data.shape == (4, 4)


@pytest.mark.skip(reason="Not sure how to test this yet.")
def test__get_uncertainty(testnd):
    # Set the uncertainty of testnd to be a lazy array
    def gen_lazy():
        lazy_loadable = FitsLazyLoadable(
            fits.ImageHDU(
                data=np.ones((5, 5)),
                header=fits.Header(
                    cards=[
                        fits.Card("EXTNAME", "bing"),
                        fits.Card("BITPIX", 32),
                    ]
                ),
                do_not_scale_image_data=True,
            )
        )

        return lazy_loadable

    # Default (section is None)
    testnd.uncertainty = gen_lazy()
    result = testnd._get_uncertainty(section=None)

    assert isinstance(result, ADVarianceUncertainty)
    assert_array_equal(result.array, testnd.variance)

    # Section is a slice
    testnd.uncertainty = gen_lazy()
    result = testnd._get_uncertainty(section=slice(0, 2))

    assert isinstance(result, ADVarianceUncertainty)
    assert_array_equal(result.array, testnd.variance[:2])

    # Section is a tuple of slices
    testnd.uncertainty = gen_lazy()
    result = testnd._get_uncertainty(section=(slice(0, 2), slice(0, 2)))

    assert isinstance(result, ADVarianceUncertainty)
    assert_array_equal(result.array, testnd.variance[:2, :2])

    # Section is a tuple of slices and ints
    testnd.uncertainty = gen_lazy()
    result = testnd._get_uncertainty(section=(slice(0, 2), 0))

    assert isinstance(result, ADVarianceUncertainty)
    assert_array_equal(result.array, testnd.variance[:2, 0])


if __name__ == "__main__":
    pytest.main()

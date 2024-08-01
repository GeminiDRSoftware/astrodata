# Disable pylint
# pylint: skip-file
from copy import deepcopy
import operator
import os

import numpy as np
import pytest
from numpy.testing import assert_array_equal

import astrodata
from astropy.io import fits
from astropy.nddata import NDData, VarianceUncertainty
from astropy.table import Table

SHAPE = (40, 50)


@pytest.fixture
def ad1():
    hdr = fits.Header({"INSTRUME": "darkimager", "OBJECT": "M42"})
    phu = fits.PrimaryHDU(header=hdr)
    hdu = fits.ImageHDU(data=np.ones(SHAPE), name="SCI")
    return astrodata.create(phu, [hdu])


@pytest.fixture
def ad2():
    phu = fits.PrimaryHDU()
    hdu = fits.ImageHDU(data=np.ones(SHAPE) * 2, name="SCI")
    return astrodata.create(phu, [hdu])


def test_attributes(ad1):
    assert ad1[0].shape == SHAPE

    data = ad1[0].data
    assert_array_equal(data, 1)
    assert data.mean() == 1
    assert np.median(data) == 1

    assert ad1.phu["INSTRUME"] == "darkimager"
    assert ad1.instrument() == "darkimager"
    assert ad1.object() == "M42"


@pytest.mark.parametrize(
    "op, res, res2",
    [
        (operator.add, 3, 3),
        (operator.sub, -1, 1),
        (operator.mul, 2, 2),
        (operator.truediv, 0.5, 2),
    ],
)
def test_arithmetic(op, res, res2, ad1, ad2):
    for data in (ad2, ad2.data):
        result = op(ad1, data)
        assert_array_equal(result.data, res)
        assert isinstance(result, astrodata.AstroData)
        assert len(result) == 1
        assert isinstance(result[0].data, np.ndarray)
        assert isinstance(result[0].hdr, fits.Header)

        result = op(data, ad1)
        assert_array_equal(result.data, res2)

    for data in (ad2[0], ad2[0].data):
        result = op(ad1[0], data)
        assert_array_equal(result.data, res)
        assert isinstance(result, astrodata.AstroData)
        assert len(result) == 1
        assert isinstance(result[0].data, np.ndarray)
        assert isinstance(result[0].hdr, fits.Header)

    # FIXME: should work also with ad2[0].data, but crashes
    result = op(ad2[0], ad1[0])
    assert_array_equal(result.data, res2)


@pytest.mark.parametrize(
    "op, res, res2",
    [
        (operator.iadd, 3, 3),
        (operator.isub, -1, 1),
        (operator.imul, 2, 2),
        (operator.itruediv, 0.5, 2),
    ],
)
def test_arithmetic_inplace(op, res, res2, ad1, ad2):
    for data in (ad2, ad2.data):
        ad = deepcopy(ad1)
        op(ad, data)
        assert_array_equal(ad.data, res)
        assert isinstance(ad, astrodata.AstroData)
        assert len(ad) == 1
        assert isinstance(ad[0].data, np.ndarray)
        assert isinstance(ad[0].hdr, fits.Header)

    # data2 = deepcopy(ad2[0])
    # op(data2, ad1)
    # assert_array_equal(data2, res2)

    for data in (ad2[0], ad2[0].data):
        ad = deepcopy(ad1)
        op(ad[0], data)
        assert_array_equal(ad.data, res)
        assert isinstance(ad, astrodata.AstroData)
        assert len(ad) == 1
        assert isinstance(ad[0].data, np.ndarray)
        assert isinstance(ad[0].hdr, fits.Header)


@pytest.mark.parametrize(
    "op, res",
    [
        (operator.add, (3, 7)),
        (operator.sub, (-1, 3)),
        (operator.mul, (2, 10)),
        (operator.truediv, (0.5, 2.5)),
    ],
)
def test_arithmetic_multiple_ext(op, res, ad1):
    ad1.append(np.ones(SHAPE, dtype=np.uint16) + 4)

    result = op(ad1, 2)
    assert len(result) == 2
    assert_array_equal(result[0].data, res[0])
    assert_array_equal(result[1].data, res[1])

    for i, ext in enumerate(ad1):
        result = op(ext, 2)
        assert len(result) == 1
        assert_array_equal(result[0].data, res[i])


@pytest.mark.parametrize(
    "op, res",
    [
        (operator.iadd, (3, 7)),
        (operator.isub, (-1, 3)),
        (operator.imul, (2, 10)),
        (operator.itruediv, (0.5, 2.5)),
    ],
)
def test_arithmetic_inplace_multiple_ext(op, res, ad1):
    ad1.append(np.ones(SHAPE, dtype=np.uint16) + 4)

    ad = deepcopy(ad1)
    result = op(ad, 2)
    assert len(result) == 2
    assert_array_equal(result[0].data, res[0])
    assert_array_equal(result[1].data, res[1])

    # Making a deepcopy will create a single nddata object but not sliced
    # as it is now independant from its parent
    for i, ext in enumerate(ad1):
        ext = deepcopy(ext)
        result = op(ext, 2)
        assert len(result) == 1
        assert_array_equal(result[0].data, res[i])

    # Now work directly on the input object, will creates single ad objects
    for i, ext in enumerate(ad1):
        result = op(ext, 2)
        assert len(result) == 1
        assert_array_equal(result.data, res[i])


@pytest.mark.parametrize(
    "op, arg, res",
    [
        ("add", 100, 101),
        ("subtract", 100, -99),
        ("multiply", 3, 3),
        ("divide", 2, 0.5),
    ],
)
def test_operations(ad1, op, arg, res):
    result = getattr(ad1, op)(arg)
    assert_array_equal(result.data, res)
    assert isinstance(result, astrodata.AstroData)
    assert isinstance(result[0].data, np.ndarray)
    assert isinstance(result[0].hdr, fits.Header)
    assert len(result) == 1


def test_operate():
    ad = astrodata.create({})
    nd = NDData(
        data=[[1, 2], [3, 4]],
        uncertainty=VarianceUncertainty(np.ones((2, 2))),
        mask=np.identity(2),
        meta={"header": fits.Header()},
    )
    ad.append(nd)

    ad.operate(np.sum, axis=1)
    assert_array_equal(ad[0].data, [3, 7])
    assert_array_equal(ad[0].variance, [2, 2])
    assert_array_equal(ad[0].mask, [1, 1])


def test_write_and_read(tmp_path, capsys):
    ad = astrodata.create({})
    nd = NDData(
        data=[[1, 2], [3, 4]],
        uncertainty=VarianceUncertainty(np.ones((2, 2))),
        mask=np.identity(2),
        meta={"header": fits.Header()},
    )
    ad.append(nd)

    tbl = Table([np.zeros(10), np.ones(10)], names=("a", "b"))

    with pytest.raises(
        ValueError, match="Tables should be set directly as attribute"
    ):
        ad.append(tbl, name="BOB")

    ad.BOB = tbl

    tbl = Table([np.zeros(5) + 2, np.zeros(5) + 3], names=("c", "d"))

    match = "Cannot append table 'BOB' because it would hide a top-level table"
    with pytest.raises(ValueError, match=match):
        ad[0].BOB = tbl

    ad[0].BOB2 = tbl
    ad[0].MYVAL_WITH_A_VERY_LONG_NAME = np.arange(10)

    match = "You can only append NDData derived instances at the top level"
    with pytest.raises(TypeError, match=match):
        ad[0].MYNDD = NDData(data=np.ones(10), meta={"header": fits.Header()})

    testfile = str(os.path.join(tmp_path, "testfile.fits"))
    ad.write(testfile)

    ad = astrodata.from_file(testfile)
    ad.info()
    captured = capsys.readouterr()

    # Windows uses int32, linux/OSX uses int64
    if os.name == "nt":
        scifmt = "int32"
        valfmt = "int32"

    elif os.name == "posix":
        scifmt = "int64"
        valfmt = "int64"

    else:
        raise ValueError(f"Unsupported OS: {os.name}")

    assert captured.out.splitlines()[3:] == [
        "Pixels Extensions",
        "Index  Content                  Type              Dimensions     Format",
        f"[ 0]   science                  NDAstroData       (2, 2)         {scifmt}",
        "          .variance             ADVarianceUncerta (2, 2)         float64",
        "          .mask                 ndarray           (2, 2)         uint16",
        "          .BOB2                 Table             (5, 2)         n/a",
        f"          .MYVAL_WITH_A_VERY_LO ndarray           (10,)          {valfmt}",
        "",
        "Other Extensions",
        "               Type        Dimensions",
        ".BOB           Table       (10, 2)",
    ]

    assert_array_equal(ad[0].nddata.data[0], nd.data[0])
    assert_array_equal(ad[0].nddata.variance[0], nd.uncertainty.array[0])
    assert_array_equal(ad[0].nddata.mask[0], nd.mask[0])


def test_reset(ad1):
    data = np.ones(SHAPE) + 3
    with pytest.raises(ValueError):
        ad1.reset(data)

    ext = ad1[0]

    with pytest.raises(ValueError):
        ext.reset(data, mask=np.ones((2, 2)), check=True)

    with pytest.raises(ValueError):
        ext.reset(data, variance=np.ones((2, 2)), check=True)

    ext.reset(data, mask=np.ones(SHAPE), variance=np.ones(SHAPE))
    assert_array_equal(ext.data, 4)
    assert_array_equal(ext.variance, 1)
    assert_array_equal(ext.mask, 1)

    ext.reset(data, mask=None, variance=None)
    assert ext.mask is None
    assert ext.uncertainty is None

    ext.reset(np.ma.array(data, mask=np.ones(SHAPE)))
    assert_array_equal(ext.data, 4)
    assert_array_equal(ext.mask, 1)

    with pytest.raises(TypeError):
        ext.reset(data, mask=1)

    with pytest.raises(TypeError):
        ext.reset(data, variance=1)

    nd = NDData(
        data=data,
        uncertainty=VarianceUncertainty(np.ones((2, 2)) * 3),
        mask=np.ones((2, 2)) * 2,
        meta={"header": {}},
    )
    ext.reset(nd)
    assert_array_equal(ext.data, 4)
    assert_array_equal(ext.variance, 3)
    assert_array_equal(ext.mask, 2)


@pytest.fixture
def random_NDAstroData_generator():
    def _random_NDAstroData_generator(shape):
        return astrodata.NDAstroData(np.random.random(shape))

    return _random_NDAstroData_generator


# Test initialization for AstroData
def test_AstroData__init__():
    # Test initialization with no arguments
    ad = astrodata.AstroData()
    assert len(ad) == 0
    assert ad.phu == fits.Header()
    assert ad.instrument() is None
    assert ad.object() is None

    # Single data argument
    data = [astrodata.NDAstroData(np.ones((2, 2)))]

    ad = astrodata.AstroData(data, is_single=True)
    assert len(ad) == 1
    assert ad.phu == fits.Header()
    assert ad.instrument() is None
    assert ad.object() is None

    # Multiple data arguments
    data = [
        astrodata.NDAstroData(np.ones((2, 2))),
        astrodata.NDAstroData(np.ones((2, 2))),
    ]

    ad = astrodata.AstroData(data, is_single=False)

    assert len(ad) == 2
    assert ad.phu == fits.Header()
    assert ad.instrument() is None
    assert ad.object() is None
    assert ad[0].data.shape == (2, 2)
    assert ad[1].data.shape == (2, 2)

    # Test initialization with a primary header
    hdr = fits.Header({"INSTRUME": "darkimager", "OBJECT": "M42"})
    phu = fits.PrimaryHDU(header=hdr)

    with pytest.raises(TypeError):
        ad = astrodata.AstroData(hdr)

    with pytest.raises(TypeError):
        ad = astrodata.AstroData(phu)

    # Test initialization with a primary header and data
    ad = astrodata.AstroData(data, phu=phu)


def test_single_nddata():
    # Test when data is a single NDData object
    data = astrodata.NDAstroData(np.ones((2, 2)))
    ad = astrodata.AstroData(data, is_single=True)
    assert len(ad) == 1
    assert ad.phu == fits.Header()
    assert ad.instrument() is None


def test_bad_tables():
    # Error should be raised if a table is not a dict
    data = [astrodata.NDAstroData(np.ones((2, 2)))]
    tbl = Table([np.zeros(10), np.ones(10)], names=("a", "b"))

    with pytest.raises(ValueError):
        astrodata.AstroData(data, is_single=True, tables=tbl)


def test_process_tags_is_present():
    # When is_present is True, tags are tested to ensure teh correct tags are
    # present and the correct number of tags are present.
    from astrodata.utils import TagSet

    # Create a TagSet that requires other tags to be present.
    class TestAstroData(astrodata.AstroData):
        @astrodata.astro_data_tag
        def _tag_self(self):
            tags = TagSet(
                {"A", "B", "C", "D"},
                if_present={"blah", "bing", "bong"},
            )
            return tags

    # Create an AstroData object without the required tags present.
    nddata = astrodata.NDAstroData(np.ones((2, 2)))
    ad = TestAstroData([nddata])

    # Check that the tags are present.
    assert ad.tags == set()

    # Add the required tags.
    class NewTestAstroData(TestAstroData):
        @astrodata.astro_data_tag
        def _other_tags(self):
            tags = TagSet({"blah", "bing", "bong"})
            return tags

    # Create an AstroData object with the required tags present.
    ad = NewTestAstroData([nddata])

    # Check that the tags are present.
    assert ad.tags == {"A", "B", "C", "D", "blah", "bing", "bong"}


def test_absolute_path_filename(tmp_path, ad1):
    # Make a temporary directory and set the filename to be an absolute path.
    path = os.path.abspath(str(tmp_path))
    filename = os.path.join(path, "test.fits")

    with pytest.raises(ValueError):
        ad1.filename = filename


def test_setter_orig_filename(tmp_path, ad1):
    ad1.orig_filename = os.path.join(tmp_path, "test.fits")


def test_multi_slice_wcs(ad1):
    ad1.is_single = False
    with pytest.raises(ValueError):
        ad1[0:2].wcs


def test_pixel_info(ad1):
    # Test pixel information for a single NDAstroData object
    pixel_info = ad1._pixel_info()

    for pixel in pixel_info:
        assert isinstance(pixel, dict)

    # Test pixel information for multiple NDAstroData objects
    ad1.is_single = False
    pixel_info = ad1._pixel_info()

    for pixel in pixel_info:
        assert isinstance(pixel, dict)

    nddata = astrodata.NDAstroData(np.ones((2, 2)))

    for nd in ad1._nddata:
        for name in tuple(sorted(nd.meta["other"])):
            if hasattr(nd.meta["other"][name], "dtype"):
                del nd.meta["other"][name].dtype

            nd.meta["other"][name].data = nddata

    pixel_info = ad1._pixel_info()

    for pixel in pixel_info:
        assert isinstance(pixel, dict)

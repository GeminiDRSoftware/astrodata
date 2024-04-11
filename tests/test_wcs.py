import itertools
import math
import os

import pytest

import numpy as np
from numpy.testing import assert_allclose

import astropy.coordinates as coord
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.modeling import models
from astropy.wcs import WCS
from astropy.io import fits

from gwcs import coordinate_frames as cf, wcs
from gwcs.wcs import WCS as gWCS

from astrodata import wcs as adwcs
from astrodata.testing import download_from_archive, skip_if_download_none
import astrodata

# from gempy.library.transform import add_longslit_wcs


@pytest.fixture(scope="module")
def F2_IMAGE():
    """Any F2 image with CD3_3=1"""
    return download_from_archive("S20130717S0365.fits")


@pytest.fixture(scope="module")
def NIRI_IMAGE():
    """Any NIRI image"""
    return download_from_archive("N20180102S0392.fits")


@pytest.fixture(scope="module")
def GMOS_LONGSLIT():
    """Any GMOS longslit spectrum"""
    return download_from_archive("N20180103S0332.fits")


@pytest.mark.parametrize("angle", [0, 20, 67, -35])
@pytest.mark.parametrize("scale", [0.5, 1.0, 2.0])
@pytest.mark.parametrize("xoffset,yoffset", [(0, 0), (10, 20)])
def test_calculate_affine_matrices(angle, scale, xoffset, yoffset):
    m = (
        (models.Scale(scale) & models.Scale(scale))
        | models.Rotation2D(angle)
        | (models.Shift(xoffset) & models.Shift(yoffset))
    )
    affine = adwcs.calculate_affine_matrices(m, (100, 100))
    assert_allclose(affine.offset, (yoffset, xoffset), atol=1e-10)
    angle = math.radians(angle)
    assert_allclose(
        affine.matrix,
        (
            (scale * math.cos(angle), scale * math.sin(angle)),
            (-scale * math.sin(angle), scale * math.cos(angle)),
        ),
        atol=1e-10,
    )


# TODO
@pytest.mark.skip(reason="WCS unused axes problem")
@skip_if_download_none
@pytest.mark.dragons_remote_data
def test_reading_and_writing_sliced_image(F2_IMAGE, tmp_path):
    ad = astrodata.from_file(F2_IMAGE)
    result = ad[0].wcs(100, 100, 0)

    ad[0].reset(ad[0].nddata[0])
    assert_allclose(ad[0].wcs(100, 100), result)

    test_file_loc = os.path.join(tmp_path, "test.fits")

    ad.write(test_file_loc, overwrite=True)
    ad2 = astrodata.from_file(test_file_loc)
    assert_allclose(ad2[0].wcs(100, 100), result)

    ad2.write(test_file_loc, overwrite=True)
    ad2 = astrodata.from_file(test_file_loc)
    assert_allclose(ad2[0].wcs(100, 100), result)


def test_remove_axis_from_model():
    """A simple test that removes one of three &-linked models"""
    model = models.Shift(0) & models.Shift(1) & models.Shift(2)

    for axis in (0, 1, 2):
        new_model, input_axis = adwcs.remove_axis_from_model(model, axis)
        assert input_axis == axis
        assert new_model.n_submodels == 2
        assert new_model.offset_0 + new_model.offset_1 == 3 - axis


def test_remove_axis_from_model_2():
    """A test with |-chained models"""
    model = (models.Shift(0) & models.Shift(1) & models.Shift(2)) | (
        models.Scale(2) & models.Rotation2D(90)
    )
    new_model, input_axis = adwcs.remove_axis_from_model(model, 0)

    assert input_axis == 0
    assert new_model.n_submodels == 3
    assert new_model.offset_0 == 1
    assert new_model.offset_1 == 2
    assert new_model.angle_2 == 90


def test_remove_axis_from_model_3():
    """A test with a Mapping"""
    model1 = models.Mapping((1, 2, 0))
    model2 = models.Shift(0) & models.Shift(1) & models.Shift(2)
    new_model, input_axis = adwcs.remove_axis_from_model(model1 | model2, 1)

    assert input_axis == 2
    assert new_model.n_submodels == 3
    assert_allclose(new_model(0, 10), (10, 2))

    new_model, input_axis = adwcs.remove_axis_from_model(model2 | model1, 1)

    assert input_axis == 2
    assert new_model.n_submodels == 3
    assert_allclose(new_model(0, 10), (11, 0))


def test_remove_axis_from_model_4():
    """A test with a Mapping that creates a new axis"""
    model1 = models.Shift(0) & models.Shift(1) & models.Shift(2)
    model = models.Mapping((1, 0, 0)) | model1
    new_model, input_axis = adwcs.remove_axis_from_model(model, 1)
    assert input_axis is None
    assert new_model.n_submodels == 3
    assert_allclose(new_model(0, 10), (10, 2))

    # Check that we can identify and remove the "Identity"-like residual Mapping
    model = models.Mapping((0, 1, 0)) | model1
    new_model, input_axis = adwcs.remove_axis_from_model(model, 2)
    assert input_axis is None
    assert new_model.n_submodels == 2
    assert_allclose(new_model(0, 10), (0, 11))


def test_remove_axis_from_model_5():
    """A test with fix_inputs"""
    model1 = models.Shift(0) & models.Shift(1) & models.Shift(2)
    model = models.fix_inputs(model1, {1: 6})
    new_model, input_axis = adwcs.remove_axis_from_model(model, 1)
    assert input_axis is None
    assert new_model.n_submodels == 2
    assert_allclose(new_model(0, 10), (0, 12))

    new_model, input_axis = adwcs.remove_axis_from_model(model, 2)
    assert input_axis == 2
    assert new_model.n_submodels == 3
    assert_allclose(new_model(0), (0, 7))


@skip_if_download_none
@pytest.mark.dragons_remote_data
def test_remove_unused_world_axis(F2_IMAGE):
    """A test with an intermediate frame"""
    ad = astrodata.from_file(F2_IMAGE)
    result = ad[0].wcs(1000, 1000, 0)
    new_frame = cf.Frame2D(name="intermediate")
    new_model = models.Shift(100) & models.Shift(200) & models.Identity(1)
    ad[0].wcs.insert_frame(ad[0].wcs.input_frame, new_model, new_frame)
    ad[0].reset(ad[0].nddata[0])
    new_result = ad[0].wcs(900, 800)
    assert_allclose(new_result, result)
    adwcs.remove_unused_world_axis(ad[0])
    new_result = ad[0].wcs(900, 800)
    assert_allclose(new_result, result[:2])
    for frame in ad[0].wcs.available_frames:
        assert getattr(ad[0].wcs, frame).naxes == 2


@skip_if_download_none
@pytest.mark.dragons_remote_data
def test_gwcs_creation(NIRI_IMAGE):
    """Test that the gWCS object for an image agrees with the FITS WCS"""
    ad = astrodata.from_file(NIRI_IMAGE)
    w = WCS(ad[0].hdr)
    for y in range(0, 1024, 200):
        for x in range(0, 1024, 200):
            wcs_sky = w.pixel_to_world(x, y)
            gwcs_sky = SkyCoord(*ad[0].wcs(x, y), unit=u.deg)
            assert wcs_sky.separation(gwcs_sky) < 0.01 * u.arcsec


# TODO: LEAVING IN FOR COMPARISON TO DRAGONS TESTS, AND TO REMEMBER DURING TEST
# MIGRATION
#
# @skip_if_download_none
# @pytest.mark.dragons_remote_data
# def test_adding_longslit_wcs(GMOS_LONGSLIT):
#     """Test that adding the longslit WCS doesn't interfere with the sky
#     coordinates of the WCS"""
#     ad = astrodata.from_file(GMOS_LONGSLIT)
#     frame_name = ad[4].hdr.get("RADESYS", ad[4].hdr["RADECSYS"]).lower()
#     crpix1 = ad[4].hdr["CRPIX1"] - 1
#     crpix2 = ad[4].hdr["CRPIX2"] - 1
#     gwcs_sky = SkyCoord(
#         *ad[4].wcs(crpix1, crpix2), unit=u.deg, frame=frame_name
#     )
#     add_longslit_wcs(ad)
#     gwcs_coords = ad[4].wcs(crpix1, crpix2)
#     new_gwcs_sky = SkyCoord(*gwcs_coords[1:], unit=u.deg, frame=frame_name)
#     assert gwcs_sky.separation(new_gwcs_sky) < 0.01 * u.arcsec
#     # The sky coordinates should not depend on the x pixel value
#     gwcs_coords = ad[4].wcs(0, crpix2)
#     new_gwcs_sky = SkyCoord(*gwcs_coords[1:], unit=u.deg, frame=frame_name)
#     assert gwcs_sky.separation(new_gwcs_sky) < 0.01 * u.arcsec
#
#     # The sky coordinates also should not depend on the extension
#     # there are shifts of order 1 pixel because of the rotations of CCDs 1
#     # and 3, which are incorporated into their raw WCSs. Remember that the
#     # 12 WCSs are independent at this stage, they don't all map onto the
#     # WCS of the reference extension
#     for ext in ad:
#         gwcs_coords = ext.wcs(0, crpix2)
#         new_gwcs_sky = SkyCoord(*gwcs_coords[1:], unit=u.deg, frame=frame_name)
#         assert gwcs_sky.separation(new_gwcs_sky) < 0.1 * u.arcsec
#
#     # This is equivalent to writing to disk and reading back in
#     wcs_dict = astrodata.wcs.gwcs_to_fits(ad[4].nddata, ad.phu)
#     new_gwcs = astrodata.wcs.fitswcs_to_gwcs(Header(wcs_dict))
#     gwcs_coords = new_gwcs(crpix1, crpix2)
#     new_gwcs_sky = SkyCoord(*gwcs_coords[1:], unit=u.deg, frame=frame_name)
#     assert gwcs_sky.separation(new_gwcs_sky) < 0.01 * u.arcsec
#     gwcs_coords = new_gwcs(0, crpix2)
#     new_gwcs_sky = SkyCoord(*gwcs_coords[1:], unit=u.deg, frame=frame_name)
#     assert gwcs_sky.separation(new_gwcs_sky) < 0.01 * u.arcsec


@skip_if_download_none
@pytest.mark.dragons_remote_data
def test_loglinear_axis(NIRI_IMAGE):
    """Test that we can add a log-linear axis and write and read it"""
    ad = astrodata.from_file(NIRI_IMAGE)
    coords = ad[0].wcs(200, 300)
    ad[0].data = np.repeat(ad[0].data[np.newaxis], 5, axis=0)
    new_input_frame = adwcs.pixel_frame(3)
    loglinear_frame = cf.SpectralFrame(
        axes_order=(0,),
        unit=u.nm,
        axes_names=("AWAV",),
        name="Wavelength in air",
    )
    celestial_frame = ad[0].wcs.output_frame
    celestial_frame._axes_order = (1, 2)
    new_output_frame = cf.CompositeFrame(
        [loglinear_frame, celestial_frame], name="world"
    )
    new_wcs = (
        models.Exponential1D(amplitude=1, tau=2) & ad[0].wcs.forward_transform
    )
    ad[0].wcs = gWCS([(new_input_frame, new_wcs), (new_output_frame, None)])
    new_coords = ad[0].wcs(2, 200, 300)
    assert_allclose(coords, new_coords[1:])

    # with change_working_dir():
    ad.write("test.fits", overwrite=True)
    ad2 = astrodata.from_file("test.fits")
    assert_allclose(ad2[0].wcs(2, 200, 300), new_coords)


@pytest.fixture
def random_wcs_and_header():
    # Construct a gwcs object with random parameters
    # This follows the guide in the gwcs documentation
    # http://gg.gg/docs-gwcs-obj-ex
    pixelshift = models.Shift(-500) & models.Shift(-500)

    # Scale by 0.1 arcsec/pixel
    pixelscale = models.Scale(0.1 / 3600.0) & models.Scale(0.1 / 3600.0)
    tangent_projection = models.Pix2Sky_TAN()
    celestial_rotation = models.RotateNative2Celestial(30.0, 45.0, 180.0)

    det2sky = pixelshift | pixelscale | tangent_projection | celestial_rotation

    detector_frame = cf.Frame2D(
        name="detector",
        axes_names=("x", "y"),
        unit=(u.pix, u.pix),
    )

    sky_frame = cf.CelestialFrame(
        reference_frame=coord.ICRS(),
        name="icrs",
        unit=(u.deg, u.deg),
    )

    wcsobj = wcs.WCS([(detector_frame, det2sky), (sky_frame, None)])
    wcsobj.bounding_box = ((-2048, 2047), (-2048, 2047))

    # Create a FITS header from the WCS object
    header = wcsobj.to_fits()[0]

    # Create astrodata-specific header entries
    for i in range(1, wcsobj.pixel_n_dim + 1):
        for j in range(1, wcsobj.world_n_dim + 1):
            header[f"CD{i}_{j}"] = 0.0

    header["WCSDIM"] = len(wcsobj.output_frame.axes_names)

    return wcsobj, header


@pytest.mark.skip(reason="Not working")
def test_fitswcs_to_gwcs(random_wcs_and_header):
    gwcs_obj, header = random_wcs_and_header
    new_gwcs = adwcs.fitswcs_to_gwcs(header, raise_errors=True)

    assert new_gwcs.input_frame.name == "pixels"
    assert new_gwcs.output_frame.name == "world"

    # Check that the two gWCS objects are equivalent
    sample = list(itertools.product(range(-1000, 1001), repeat=2))
    rng = np.random.default_rng(0)
    rng.shuffle(sample)
    sample = sample[:1000] + [(0, 0)]
    for x, y in sample:
        assert_allclose(
            gwcs_obj(x, y),
            new_gwcs(x, y),
            atol=1e-9,
        )

        # Round-trip test
        assert_allclose(
            new_gwcs.numerical_inverse(*new_gwcs(x, y)),
            (x, y),
            atol=1e-9,
        )


def test_fitswcs_to_gwcs_raise_errors():
    err_msg = "Expected a FITS Header, dict, or NDData object"

    with pytest.raises(TypeError, match=err_msg):
        adwcs.fitswcs_to_gwcs("blah", raise_errors=True)


@pytest.mark.skip(reason="Not working")
def test_gwcs_to_fits(random_wcs_and_header):
    gwcs_obj, header = random_wcs_and_header

    # Need to attach the gwcs to a dummy primary header unit to use the
    # gWCS to FITS conversion
    phu = fits.PrimaryHDU()
    phu.data = np.zeros((2048, 2048))
    # Add a few features to the data
    phu.data += np.zeros((2048, 2048)) + np.arange(2048)[:, np.newaxis]

    ndd = astrodata.create(phu)
    ndd.is_single = True
    ndd.wcs = gwcs_obj

    new_header = adwcs.gwcs_to_fits(ndd)

    # Check that the two FITS headers are equivalent
    header_dict = dict(header)

    different_keys = {k for k in new_header if k not in header_dict}
    assert not different_keys, f"Different keys: {different_keys}"

    different_vals = {
        k: (v1, header_dict[k])
        for (k, v1) in new_header.items()
        if v1 != header_dict[k]
    }

    # TODO: Ignoring some values calculated by astrodata (e.g., from the affine
    # matrices) for now. Those are tested elsewhere, but it would be good to
    # consolidate it here too.
    ignore_keys = {"CRVAL1", "CRVAL2", "CD1_1", "CD1_2", "CD2_1", "CD2_2"}
    different_vals = {
        k: v for k, v in different_vals.items() if k not in ignore_keys
    }

    assert not different_vals, f"Different values: {different_vals}"

    # Check that the WCS object can be reconstructed from the FITS header
    new_gwcs = adwcs.fitswcs_to_gwcs(new_header)
    sample = list(itertools.product(range(-1000, 1001), repeat=2))
    rng = np.random.default_rng(0)
    rng.shuffle(sample)
    sample = sample[:1000] + [(0, 0)]
    for x, y in sample:
        assert_allclose(
            gwcs_obj(x, y),
            new_gwcs(x, y),
            atol=1e-9,
        )

        # Round-trip test
        assert_allclose(
            new_gwcs.numerical_inverse(*new_gwcs(x, y)),
            (x, y),
            atol=1e-9,
        )

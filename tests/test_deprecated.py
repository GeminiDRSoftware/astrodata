"""This test file is meant to test that deprecated functions either raise the
appropriate warning or error. It does not check for their functionality (which
is covered by the functions that are replacing them, anyways).
"""

import astrodata
import astropy.io.fits as fits
import pytest
import os

from astrodata.utils import AstroDataDeprecationWarning


@pytest.fixture
def example_fits_file(tmp_path) -> str:
    """Create an empty fits file, and return the path."""
    filename = os.path.join(tmp_path, "example.fits")
    hdu = fits.PrimaryHDU()
    hdu.writeto(filename)
    return filename


@pytest.fixture
def example_ad_class():
    class ExampleAdClass(astrodata.AstroData):
        pass

    return ExampleAdClass


@pytest.fixture
def example_phu():
    return fits.PrimaryHDU(data=[1, 2, 3])


@pytest.fixture
def example_extensions(example_phu):
    extension = fits.ImageHDU(data=[1, 2, 3])
    return [example_phu, extension]


@pytest.fixture
def ad(example_fits_file):
    return astrodata.from_file(example_fits_file)


def test_open(example_fits_file):
    with pytest.warns(AstroDataDeprecationWarning):
        astrodata.open(example_fits_file)


def test_deprecated_astrodata_header(ad):
    with pytest.warns(AstroDataDeprecationWarning):
        ad.header


def test_deprecated_astrodatafactory_openFile(example_fits_file):
    with pytest.warns(AstroDataDeprecationWarning):
        astrodata.factory._openFile(example_fits_file)


def test_deprecated_astrodatafactory_addClass(example_ad_class):
    with pytest.warns(AstroDataDeprecationWarning):
        astrodata.factory.addClass(example_ad_class)


def test_deprecated_astrodatafactory_getAstroData(example_fits_file):
    with pytest.warns(AstroDataDeprecationWarning):
        astrodata.factory.getAstroData(example_fits_file)


def test_deprecated_astrodatafactory_createFromScratch(
    example_phu, example_extensions
):
    with pytest.warns(AstroDataDeprecationWarning):
        astrodata.factory.createFromScratch(example_phu, example_extensions)

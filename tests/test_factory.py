# Disable pylint
# pylint: skip-file

import pytest

import os

import astrodata
from astrodata import factory

from astropy.io import fits


pytest.skip("Not yet functional.", allow_module_level=True)

# TODO: using aliases here...
adfactory = factory.AstroDataFactory


@pytest.fixture
def example_fits_file(tmp_path) -> str:
    """Create an empty fits file, and return the path."""
    filename = os.path.join(tmp_path, "example.fits")
    hdu = fits.PrimaryHDU(data=[1, 2, 3])
    hdu.writeto(filename)
    return filename


@pytest.fixture
def example_phu():
    return fits.PrimaryHDU(data=[1, 2, 3])


@pytest.fixture
def example_extensions(example_phu):
    extension = fits.ImageHDU(data=[1, 2, 3])
    return [example_phu, extension]


@pytest.fixture
def ad(example_fits_file) -> astrodata.AstroData:
    return astrodata.from_file(example_fits_file)


@pytest.fixture
def nonexistent_file(tmp_path) -> str:
    filename = os.path.join(tmp_path, "nonexistent.fits")

    if os.path.isfile(filename):
        os.remove(filename)

    return filename


@pytest.fixture
def example_dir(tmp_path) -> str:
    # Make an empty directory.
    dirname = os.path.join(tmp_path, "example_directory")

    if os.path.exists(dirname):
        os.remove(dirname)

    os.mkdir(dirname)

    return dirname


def test__open_file(example_fits_file):
    # str/pathlike both have the same outcome
    adfactory._open_file(example_fits_file)


def test__open_file_file_not_found(nonexistent_file, example_dir):
    # TODO: Add hypothesis testing here for edge cases and such.
    # Check that correct error is raised if the file doesn't exist
    with pytest.raises(FileNotFoundError):
        with adfactory._open_file(nonexistent_file) as _:
            pass

    # Check passing a directory.
    with pytest.raises(FileNotFoundError):
        with adfactory._open_file(example_dir) as _:
            pass

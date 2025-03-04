from copy import deepcopy
import os

import astrodata
from astrodata import adfactory
from astrodata import AstroData

from astropy.io import fits

import pytest


factory = adfactory.AstroDataFactory


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
    factory._open_file(example_fits_file)


def test__open_file_file_not_found(nonexistent_file, example_dir):
    # Check that correct error is raised if the file doesn't exist
    with pytest.raises(FileNotFoundError):
        with factory._open_file(nonexistent_file) as _:
            pass

    # Check passing a directory.
    with pytest.raises(FileNotFoundError):
        with factory._open_file(example_dir) as _:
            pass

def test_report_all_exceptions_on_failure_get_astro_data(example_fits_file, monkeypatch, capfd,):
    """Tests that all exceptions are reported if file fails to open.

    This test tries to capture errors that were previously discarded. It does
    this by checking what is sent to stderr/stdout.

    In the future, when support for python 3.10 is dropped, exception groups
    would vastly simplify this.
    """
    # Use local adfactory to avoid spoiling the main one.
    factory = astrodata.adfactory.AstroDataFactory()
    monkeypatch.setattr(astrodata, "factory", factory)

    class AD1(AstroData):
        _message = "This_is_exception_1"
        @staticmethod
        def _matches_data(source):
            raise ValueError(AD1._message)

    class AD2(AstroData):
        _message = "This_is_exception_2"
        @staticmethod
        def _matches_data(source):
            raise IndexError(AD2._message)

    class AD3(AstroData):
        _message = "This_is_exception_3"
        @staticmethod
        def _matches_data(source):
            raise Exception(AD3._message)

    classes = (AD1, AD2, AD3)

    for _cls in classes:
        astrodata.factory.add_class(_cls)

    with pytest.raises(astrodata.AstroDataError) as exception_info:
        astrodata.from_file(example_fits_file)


    caught_err = exception_info.value
    assert str(caught_err)
    assert "No class matches this dataset" in str(caught_err)

    for message in (_cls._message for _cls in classes):
        assert message in str(caught_err), str(caught_err)

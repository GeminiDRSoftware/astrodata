"""
Tests for the `RandomFitsFile` class in generate_test_data.py.
"""

import os

import astropy.io.fits as fits
import numpy as np
from astropy.nddata import NDData
from astropy.units import Quantity

from generate_test_data import RandomFitsFile


def test_set_seed():
    RandomFitsFile.set_seed(123)
    assert RandomFitsFile.get_seed() == 123


def test_generate_random_data():
    RandomFitsFile.set_seed(123)
    data = RandomFitsFile.generate_random_data((10, 10))
    assert isinstance(data, np.ndarray)
    assert data.shape == (10, 10)


def test_generate_random_shaped_data():
    RandomFitsFile.set_seed(123)
    data = RandomFitsFile.generate_random_shaped_data()
    assert isinstance(data, np.ndarray)


def test_generate_random_numpy_array():
    RandomFitsFile.set_seed(123)
    data = RandomFitsFile.generate_random_numpy_array()
    assert isinstance(data, np.ndarray)


def test_generate_random_nddata():
    RandomFitsFile.set_seed(123)
    data = RandomFitsFile.generate_random_nddata()
    assert isinstance(data, NDData)


def test_generate_random_quantity():
    RandomFitsFile.set_seed(123)
    data = RandomFitsFile.generate_random_quantity()
    assert isinstance(data, Quantity)


def test_generate_random_file_name():
    RandomFitsFile.set_seed(123)
    filename = RandomFitsFile.generate_random_file_name()
    assert isinstance(filename, str)
    assert filename.endswith(".fits")


def test_write_fits_file(tmpdir):
    RandomFitsFile.set_seed(123)
    data = RandomFitsFile.generate_random_data((10, 10))
    filename = "test.fits"
    path = str(tmpdir)
    RandomFitsFile.write_fits_file(data, filename, path)
    assert os.path.exists(os.path.join(path, filename))
    hdul = fits.open(os.path.join(path, filename))
    assert isinstance(hdul[0].data, np.ndarray)
    assert hdul[0].data.shape == (10, 10)
    hdul.close()


def test_create_random_files(tmpdir):
    RandomFitsFile.set_seed(123)
    files = RandomFitsFile.create_random_files(10, path=str(tmpdir))
    assert len(os.listdir(str(tmpdir))) == 10
    assert len(files) == 10

    for file in files:
        assert file.endswith(".fits")
        assert os.path.exists(os.path.join(tmpdir, file))


def test_create_random_header():
    RandomFitsFile.set_seed(123)
    header = RandomFitsFile.create_random_header()
    assert isinstance(header, fits.Header)
    assert len(header) == 10
    assert len(header.cards) == 10
    for key, value, comment in header.cards:
        assert isinstance(key, str)
        assert isinstance(value, str)
        assert isinstance(comment, str)
        assert len(key) <= 8
        assert len(value) <= 70
        assert len(comment) <= 72


def test_temp_files_context():
    with RandomFitsFile.temp_files_context(10) as files:
        assert len(files) == 10
        for file in files:
            assert file.endswith(".fits")
            assert os.path.exists(file)

    for file in files:
        assert not os.path.exists(file)

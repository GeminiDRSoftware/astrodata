"""This file contains functions for generating test data files
for the purposes of testing.

The functions in this file should be used with caution, as they
create new files and may cause issues with the github workflows if they
generate too many test files (or too many at once).
"""

import os
import string
import typing
from contextlib import contextmanager
from os.path import exists, join

import astropy.io.fits as fits
import astropy.units as u
import astropy.nddata as nddata
import numpy as np


class RandomFitsFile:
    """Class interface for generating random fits files. Caution: this uses a
    static seed stored in the RandomFitsFile._seed class attr. To set a new
    seed, use RandomFitsFile.set_seed([seed]).
    """

    _seed: int = 0
    _min_size: int = 0
    _max_size: int = 100

    @classmethod
    def set_seed(cls, seed: int):
        """Set the seed for the random number generator.

        Paramete
        ----------
        seed : int
            The seed to set.
        """
        cls._seed = seed

    @classmethod
    def get_seed(cls) -> int:
        """Retrieve the current seed for the random number generator."""
        return cls._seed

    @classmethod
    def generate_random_data(cls, shape: tuple[int] = (10, 10)):
        """Generate random data for a fits file.

        Parameters
        ----------
        shape : tuple
            The shape of the data to generate.

        Returns
        -------
        data : `numpy.ndarray`
            The generated data.
        """
        return np.random.random(shape)

    @classmethod
    def generate_random_shaped_data(cls):
        """Generate random data for a fits file with a random shape."""
        shape = np.random.randint(1, 100, 2)
        return cls.generate_random_data(shape)

    @classmethod
    def generate_random_numpy_array(cls):
        """Generate a random numpy array."""
        return cls.generate_random_shaped_data()

    @classmethod
    def generate_random_nddata(cls):
        """Generate a random NDData object."""
        return nddata.NDData(cls.generate_random_shaped_data())

    @classmethod
    def generate_random_quantity(cls):
        """Generate a random astropy quantity."""
        return u.Quantity(cls.generate_random_shaped_data())

    @classmethod
    def generate_random_file_name(
        cls, max_length: int = 100, fixed_length: int = -1
    ) -> str:
        """Generate a file name for a fits file. It will always have a .fits
        extension and the absolute path to this folder it not included in the
        max_length of the file name.

        Parameters
        ----------
        max_length : int
            The maximum length of the file name.

        fixed_length : int
            If this is not -1, then the file name will be exactly this length.

        Returns
        -------
        file_name : str
            The generated file name.
        """
        assert max_length >= fixed_length, "max_length must be >= fixed_length"

        length = fixed_length

        if length < 0:
            length = np.random.randint(cls._min_size, max_length)

        # Include any valid path characters
        valid_chars = string.ascii_letters + string.digits + "_-."

        filename = "".join(np.random.choice(list(valid_chars), length))

        filename += ".fits"

        return filename

    @classmethod
    def write_fits_file(
        cls,
        data: typing.Union[nddata.NDData, np.ndarray, u.Quantity],
        filename: str,
        path: str = "",
    ):
        """Write a fits file to disk. The file will be written to the
        test_data/data folder by default.

        Parameters
        ----------
        data : `astropy.nddata.NDData`, `numpy.ndarray`, `astropy.units.Quantity`
            The data to write to the fits file.

        filename : str
            The name of the file to write.

        path : str
            The path to write the file to.
        """
        if isinstance(data, nddata.NDData):
            data = data.data

        if isinstance(data, u.Quantity):
            data = data.value

        if not filename.endswith(".fits"):
            filename += ".fits"

        if path:
            filename = join(path, filename)

        else:
            filename = join(os.path.dirname(__file__), "data", filename)

        hdu = fits.PrimaryHDU(data)
        hdu.writeto(join(path, filename), overwrite=True)

    @classmethod
    def create_random_header_key(cls, max_key_length: int = 8) -> str:
        """Create a random header key.

        Parameters
        ----------
        max_key_length : int
            The maximum length of the header key.

        Returns
        -------
        key : str
            The generated header key.

        Notes
        -----
        The fits standard specifies that the maximum length of a header key is
        8 characters.
        """
        # Only use valid header characters according to the FITS standard.
        valid_chars = string.ascii_letters + string.digits + "-_"

        length = np.random.randint(1, max_key_length)

        return "".join(np.random.choice(list(valid_chars), length))

    @classmethod
    def create_random_header_value(cls):
        """Create a random header value that is valid under the FITS standard."""
        # Only use valid value characters according to the FITS standard.
        valid_chars = string.ascii_letters + string.digits + "-_"

        length = np.random.randint(1, 70)

        return "".join(np.random.choice(list(valid_chars), length))

    @classmethod
    def create_random_header(
        cls,
        max_key_length: int = 8,
        max_value_length: int = 70,
        cards: int = 10,
    ) -> fits.Header:
        """Create a random fits header.

        Parameters
        ----------
        max_key_length : int
            The maximum length of the header key.

        max_value_length : int
            The maximum length of the header value.

        cards : int
            The number of cards to generate.

        Returns
        -------
        header : `astropy.io.fits.Header`
            The generated header.

        Notes
        -----
        The fits standard specifies that the maximum length of a header key is
        8 characters, and the maximum length of a header value is 70 characters.
        """
        header = fits.Header()

        for _ in range(cards):
            key = ""
            while not key or key in header:
                key = cls.create_random_header_key(max_key_length)
                value = cls.create_random_header_value()

            header[key] = value

        return header

    @classmethod
    def check_if_file_exists(cls, filename: str, path: str = "") -> bool:
        """Check if a file exists.

        Parameters
        ----------
        filename : str
            The name of the file to check.

        path : str
            The path to check the file in.

        Returns
        -------
        exists : bool
            Whether or not the file exists.
        """
        if path:
            filename = join(path, filename)

        else:
            filename = join(os.path.dirname(__file__), "data", filename)

        return exists(filename)

    @classmethod
    def create_random_files(
        cls,
        count: int = 10,
        max_length: int = 100,
        fixed_length: int = -1,
        path: str = "",
    ) -> list[str]:
        """Create random fits files.

        Parameters
        ----------
        count : int
            The number of files to create.

        max_length : int
            The maximum length of the file names.

        fixed_length : int
            If this is not -1, then the file names will be exactly this length.

        path : str
            The path to create the files in. If this is not specified, then
            the files will be created in the test_data/data folder.

        Returns
        -------
        filenames : list
            The list of file names created.
        """
        files = []
        filename = None
        for _ in range(count):
            # This is dumb, should probably just make an ID at the front or
            # something.
            while not filename or cls.check_if_file_exists(filename, path):
                filename = cls.generate_random_file_name(max_length, fixed_length)

            data = cls.generate_random_data()

            cls.write_fits_file(data, filename, path=path)

            files.append(filename)

        return files

    @classmethod
    @contextmanager
    def temp_files_context(cls, count, max_length=50, fixed_length=-1, path="."):
        """Creates temporary files using a context manager, and cleans up those
        files once the run is finished.

        Parameters
        ----------
        count : int
            The number of files to create.

        max_length : int
            The maximum length of the file names.

        fixed_length : int
            If this is not -1, then the file names will be exactly this length.

        path : str
            The path to create the files in. If this is not specified, then
            the files will be created in the test_data/data folder.

        Returns
        -------
        filenames : list
            The list of file names created.
        """
        files = []
        try:
            for _ in range(count):
                filename = None

                while filename is None or exists(join(path, filename)):
                    filename = cls.generate_random_file_name(
                        max_length,
                        fixed_length,
                    )

                data = cls.generate_random_data()

                cls.write_fits_file(data, filename, path=path)

                files.append(filename)

            yield files

        finally:
            for filename in files:
                os.remove(join(path, filename))

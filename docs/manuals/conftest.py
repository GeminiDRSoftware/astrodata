"""pytest configuration for the documentation tests."""

import os

import astrodata
from astrodata import astro_data_tag, astro_data_descriptor

import astrodata.testing

import numpy

import pytest

_DOCTEST_DATA_TAG = "_DOCTEST_DATA"


@pytest.fixture(autouse=True)
def setup_doctest(doctest_namespace):
    """Set up the doctest namespace."""
    doctest_namespace["astrodata"] = astrodata
    doctest_namespace["np"] = numpy


@pytest.fixture(autouse=True)
def register_test_class(doctest_namespace, setup_doctest):
    """Register a special class of AstroData for testing the documentation."""

    class DocTestAstroData(astrodata.AstroData):
        """A special class of AstroData for testing the documentation."""

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

            # Generates an initial variance for our fake instrument.
            # This is just for testing purposes, and is *not* realistic.
            self._variance = None

        def _generate_variance(self):
            """Generate a variance plane for the data. THIS IS NOT HOW YOU
            WOULD HANDLE VARIANCE IN REAL LIFE.

            Instead, you would read the variance from the FITS file, or
            calculate it from the data itself.

            Variance Example
            ----------------
            Say you have data and the variance is some function of descriptors
            for a given data set. E.g., our variance is proportional to the
            inverse of exposure time and proportional to the data itself. Our
            variance would be:

            .. math::

                \sigma^2 = \frac{d}{t}

            where :math:`\sigma^2` is the variance, :math:`d` is the data, and
            :math:`t` is the exposure time. To assign this variance to our data, we
            would do:

            .. doctest
                    >>> from astrodata import create
                    >>> from astropy.io import fits
                    >>> image = fits.PrimaryHDU(data=[list(range(5)) for _ in range(5)])
                    >>> data = create_from_scratch(image)
                    >>> exposure_time = 2
                    >>> proportionality_constant = 0.1
                    >>> data.variance = (
                    ...     proportionality_constant * data
                    ...     / exposure_time
                    ... )
            """
            self.variance = self.data * 0.314

        @property
        def variance(self):
            """Return the variance plane."""
            if self._variance is None:
                self._generate_variance()

            return self._variance

        @variance.setter
        def variance(self, value):
            """Set the variance plane."""
            self._variance = value

        @astro_data_tag
        def doctest_data_tag(self):
            """A tag for testing the documentation."""
            return astrodata.TagSet([_DOCTEST_DATA_TAG])

        @staticmethod
        def _matches_data(source):
            """Return True if the data matches the given tags."""
            doctest_header = source[0].header.get("INSTRUME", "").upper()

            return doctest_header == "DOCTEST_INSTRUMENT"

        @astro_data_descriptor
        def exposure_time(self):
            """Return the exposure time."""
            exposure_time = self.phu.get("EXPTIME", None)

            if exposure_time is not None:
                return exposure_time

            raise AttributeError("Exposure time not found in the header.")

        @astro_data_descriptor
        def gain(self):
            """Return the gains of each image."""
            if "GAIN" in self.phu:
                return (
                    self.phu["GAIN"]
                    if self.is_single
                    else [self.phu["GAIN"]] * len(self)
                )

            if self.is_single:
                return [1.5]

            return [1.5] * len(self)

    factory = doctest_namespace["astrodata"].factory
    if not any(
        DocTestAstroData.__name__ in cls.__name__ for cls in factory.registry
    ):
        factory.add_class(DocTestAstroData)

    return DocTestAstroData


@pytest.fixture(autouse=True)
def some_fits_file(tmp_path, doctest_namespace):
    """Return the path to the primary testing FITS file."""
    filename = os.path.join(tmp_path, "some_file.fits")

    if os.path.exists(filename):
        os.remove(filename)

    # Create a test file with a PHU and single image in it.
    image_shape = (2048, 2048)
    header_keys = {
        "INSTRUME": "DOCTEST_INSTRUMENT",
        "IMG_TYPE": "TEST_IMAGE",
        "EXPTIME": 1,
    }

    fits_bytes = astrodata.testing.fake_fits_bytes(
        image_shape=image_shape,
        include_header_keys=header_keys,
        single_hdu=True,
    )

    fits_bytes.flush()
    fits_bytes.seek(0)

    with open(filename, "wb+") as f:
        for chunk in fits_bytes:
            f.write(chunk)

    doctest_namespace["some_fits_file"] = str(filename)


@pytest.fixture(autouse=True)
def some_files_file_with_extensions(tmp_path, doctest_namespace):
    """Return the path to the primary testing FITS file."""
    # Fixture constants
    n_extensions = 5
    image_shape = (2048, 2048)

    # Create a temporary file
    filename = os.path.join(tmp_path, "some_file_with_extensions.fits")

    if os.path.exists(filename):
        os.remove(filename)

    # Create a test file with a PHU and single image in it.
    header_keys = {
        "INSTRUME": "DOCTEST_INSTRUMENT",
        "IMG_TYPE": "TEST_IMAGE",
        "EXPTIME": 1,
    }

    fits_bytes = astrodata.testing.fake_fits_bytes(
        image_shape=image_shape,
        include_header_keys=header_keys,
        n_extensions=n_extensions,
    )

    fits_bytes.seek(0)

    with open(filename, "wb+") as f:
        for chunk in fits_bytes:
            f.write(chunk)

    doctest_namespace["some_fits_file_with_extensions"] = str(filename)

    return str(filename)


@pytest.fixture(autouse=True)
def some_fits_file_with_mask(
    tmp_path,
    doctest_namespace,
):
    """Return the path to the primary testing FITS file."""
    # Fixture constants
    n_extensions = 5

    # Create a temporary file
    filename = os.path.join(tmp_path, "some_file_with_mask.fits")

    if os.path.exists(filename):
        os.remove(filename)

    # Create a test file with a PHU and single image in it.
    image_shape = (100, 100)
    header_keys = {
        "INSTRUME": "DOCTEST_INSTRUMENT",
        "IMG_TYPE": "TEST_IMAGE",
        "EXPTIME": 1,
    }

    fits_bytes = astrodata.testing.fake_fits_bytes(
        image_shape=image_shape,
        include_header_keys=header_keys,
        n_extensions=n_extensions,
        masks=True,
    )

    fits_bytes.seek(0)

    with open(filename, "wb+") as f:
        for chunk in fits_bytes:
            f.write(chunk)

    doctest_namespace["some_fits_file_with_mask"] = str(filename)

    return str(filename)


@pytest.fixture(autouse=True)
def random_number(doctest_namespace):
    """Return a random number generator using the same seed every time."""
    rng = numpy.random.default_rng(42)
    doctest_namespace["random_number"] = rng

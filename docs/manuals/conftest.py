"""pytest configuration for the documentation tests."""
import os

import astrodata
from astrodata import astro_data_tag, astro_data_descriptor
from astrodata.testing import fake_fits_bytes

import pytest

__DOCTEST_DATA_TAG = "_DOCTEST_DATA"


@pytest.fixture(autouse=True)
def setup_doctest(doctest_namespace):
    """Set up the doctest namespace."""
    doctest_namespace["astrodata"] = astrodata


@pytest.fixture(autouse=True)
def register_test_class(doctest_namespace, setup_doctest):
    """Register a special class of AstroData for testing the documentation."""

    class DocTestAstroData(astrodata.AstroData):
        """A special class of AstroData for testing the documentation."""

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

        @astro_data_tag
        def doctest_data_tag(self):
            """A tag for testing the documentation."""
            return astrodata.TagSet([__DOCTEST_DATA_TAG])

        @staticmethod
        def _matches_data(source):
            """Return True if the data matches the given tags."""
            doctest_header = source[0].header.get("INSTRUME", "").upper()

            return doctest_header == "DOCTEST_INSTRUMENT"

        @astro_data_descriptor
        def exposure_time(self):
            """Return the exposure time."""
            return self[0].header.get("EXPTIME", None)

    if (
        "DocTestAstroData"
        not in doctest_namespace["astrodata"].factory.registry
    ):
        doctest_namespace["astrodata"].factory.add_class(DocTestAstroData)

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
        "IMAGE_TYPE": "TEST_IMAGE",
        "EXPTIME": 1,
    }

    fits_bytes = fake_fits_bytes(
        image_shape=image_shape,
        include_header_keys=header_keys,
        single_hdu=True,
    )

    fits_bytes.seek(0)

    with open(filename, "wb+") as f:
        for chunk in fits_bytes:
            f.write(chunk)

    doctest_namespace["some_fits_file"] = str(filename)


@pytest.fixture(autouse=True)
def some_files_file_with_extensions(tmp_path, doctest_namespace):
    """Return the path to the primary testing FITS file."""
    filename = os.path.join(tmp_path, "some_file_with_extensions.fits")

    if os.path.exists(filename):
        os.remove(filename)

    # Create a test file with a PHU and single image in it.
    image_shape = (2048, 2048)
    header_keys = {
        "INSTRUME": "DOCTEST_INSTRUMENT",
        "IMAGE_TYPE": "TEST_IMAGE",
    }

    fits_bytes = fake_fits_bytes(
        image_shape=image_shape,
        include_header_keys=header_keys,
        n_extensions=5,
    )

    fits_bytes.seek(0)

    with open(filename, "wb+") as f:
        for chunk in fits_bytes:
            f.write(chunk)

    doctest_namespace["some_fits_file_with_extensions"] = str(filename)

    return str(filename)

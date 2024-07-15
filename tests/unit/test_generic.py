"""Generic functional testing for subclassing the AstroData class using
arbitrary data.

This is meant to replicate the 'typical' use case for developers of subclassing
AstroData. While these are not exhaustive, and may contain considerable
overlaps with other tests, they are meant to ensure the basic API behaves as
expected under changes.
"""

import copy
import os

import pytest

import astropy.io.fits as fits

import numpy as np

import astrodata
from astrodata import astro_data_tag, astro_data_descriptor, TagSet


@pytest.fixture
def temporary_fits_file(tmp_path):
    """Create a temporary FITS file with a single extension."""
    filename = os.path.join(tmp_path, "test.fits")
    header = fits.Header({"INSTRUME": "TEST_INSTRUMENT"})
    hdu = fits.PrimaryHDU(
        data=np.ones((10, 10)),
        header=header,
    )

    hdu.writeto(str(filename), overwrite=True)

    return str(filename)


@pytest.fixture
def fresh_factory():
    """Return a fresh factory."""
    return astrodata.AstroDataFactory()


@pytest.fixture
def fresh_ad_factory():
    """Return a copy of the pre-initialized AstroDataFactory (imported as
    astrodata.factory).
    """
    return copy.deepcopy(astrodata.factory)


def test_create_and_register_class(
    temporary_fits_file,
    fresh_factory,
    fresh_ad_factory,
):
    """Test that a new class can be created and registered with the factory."""

    class TestClass(astrodata.AstroData):
        """A testing class for AstroData."""

        @staticmethod
        def _matches_data(source):
            return True

    factory = fresh_ad_factory
    factory.add_class(TestClass)

    ad = factory.get_astro_data(temporary_fits_file)

    assert isinstance(ad, TestClass)

    # With a fresh factory, the class should not be registered.
    factory = fresh_factory

    with pytest.raises(astrodata.AstroDataError):
        factory.get_astro_data(temporary_fits_file)

    factory.add_class(TestClass)

    ad = factory.get_astro_data(temporary_fits_file)

    assert isinstance(ad, TestClass)


def test_create_and_register_conflicting_classes(
    temporary_fits_file, fresh_factory, fresh_ad_factory
):
    """Test that a new class can be created and registered with the factory,
    and that classes conflicting by definition are caught with exceptions.
    """

    class TestClass1(astrodata.AstroData):
        """A testing class for AstroData. Matches all data."""

        @staticmethod
        def _matches_data(source):
            return True

    class TestClass2(astrodata.AstroData):
        """A testing class for AstroData. Matches all data."""

        @staticmethod
        def _matches_data(source):
            return True

    class TestClass3(astrodata.AstroData):
        """A testing class for AstroData. Matches no data."""

        @staticmethod
        def _matches_data(source):
            return False

    factory = fresh_ad_factory
    factory.add_class(TestClass1)
    factory.add_class(TestClass2)

    with pytest.raises(astrodata.AstroDataError):
        factory.get_astro_data(temporary_fits_file)

    factory.remove_class("TestClass2")
    factory.add_class(TestClass3)

    # With a fresh factory, no default classes registered.
    factory = fresh_factory

    factory.add_class(TestClass1)
    factory.add_class(TestClass2)

    with pytest.raises(astrodata.AstroDataError):
        factory.get_astro_data(temporary_fits_file)

    factory.remove_class(TestClass2)
    factory.add_class(TestClass3)


def test_create_and_register_class_with_no_matches(
    temporary_fits_file,
    fresh_factory,
    fresh_ad_factory,
):
    """Test that a new class can be created and registered with the factory."""

    class TestClass(astrodata.AstroData):
        """A testing class for AstroData."""

        @staticmethod
        def _matches_data(source):
            return False

    factory = fresh_ad_factory
    factory.add_class(TestClass)

    # Defaults to AstroData object in the pre-initialized factory.
    ad = factory.get_astro_data(temporary_fits_file)

    assert isinstance(ad, astrodata.AstroData)

    # With a fresh factory, no default classes registered.
    factory = fresh_factory

    with pytest.raises(astrodata.AstroDataError):
        factory.get_astro_data(temporary_fits_file)

    factory.add_class(TestClass)

    with pytest.raises(astrodata.AstroDataError):
        factory.get_astro_data(temporary_fits_file)


def test_create_class_with_tags(
    temporary_fits_file,
    fresh_factory,
    fresh_ad_factory,
):
    """Test that a new class can be created and registered with the factory."""

    class TestClass(astrodata.AstroData):
        """A testing class for AstroData."""

        @staticmethod
        def _matches_data(source):
            return (
                source[0].header.get("INSTRUME", "").upper()
                == "TEST_INSTRUMENT"
            )

        @astro_data_tag
        def tag1(self):
            return TagSet(["TAG1"])

        @astro_data_tag
        def tag2(self):
            return TagSet(["TAG2"])

    factory = fresh_ad_factory
    factory.add_class(TestClass)

    ad = factory.get_astro_data(temporary_fits_file)

    assert isinstance(ad, TestClass)

    # With a fresh factory, the class should not be registered.
    factory = fresh_factory

    with pytest.raises(astrodata.AstroDataError):
        factory.get_astro_data(temporary_fits_file)

    factory.add_class(TestClass)

    ad = factory.get_astro_data(temporary_fits_file)

    assert isinstance(ad, TestClass)

    # Check the tags
    print(ad.tags)
    assert ad.tags == {"TAG1", "TAG2"}


def test_create_class_with_descriptors(
    temporary_fits_file,
    fresh_factory,
    fresh_ad_factory,
):
    """Test that a new class can be created and registered with the factory."""

    class TestClass(astrodata.AstroData):
        """A testing class for AstroData."""

        @staticmethod
        def _matches_data(source):
            return (
                source[0].header.get("INSTRUME", "").upper()
                == "TEST_INSTRUMENT"
            )

        @astro_data_descriptor
        def descriptor1(self):
            return 1

        @astro_data_descriptor
        def descriptor2(self):
            return 2

    factory = fresh_ad_factory
    factory.add_class(TestClass)

    ad = factory.get_astro_data(temporary_fits_file)

    assert isinstance(ad, TestClass)

    # Check the descriptors
    assert ad.descriptor1() == 1
    assert ad.descriptor2() == 2

    # With a fresh factory, the class should not be registered.
    factory = fresh_factory

    with pytest.raises(astrodata.AstroDataError):
        factory.get_astro_data(temporary_fits_file)

    factory.add_class(TestClass)

    ad = factory.get_astro_data(temporary_fits_file)

    assert isinstance(ad, TestClass)

    # Check the descriptors
    assert ad.descriptor1() == 1
    assert ad.descriptor2() == 2

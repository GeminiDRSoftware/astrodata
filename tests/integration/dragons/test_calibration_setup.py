"""These are tests ensuring the DRAGONS calibration service functions properly
for testing purposes.
"""

from astrodata.testing import download_from_archive
import gemini_instruments  # noqa
import pytest


def all_calibration_files(calibration_service) -> list[str]:
    """Return all calibration files as a list (guraranteed).

    Required because calibration_service.list_files() returns an
    iterator, not a list.
    """
    return [f for f in calibration_service.list_files()]


@pytest.mark.dragons
def test_cal_service_add(calibration_service, tmp_path):
    """Test adding a calibration file."""
    # Download a file from the internet into a temporary directory.
    bias_file = "S20240624S0106.fits"
    file_path = download_from_archive(bias_file)
    calibration_service.add_cal(file_path)
    assert all_calibration_files(calibration_service) == [bias_file]

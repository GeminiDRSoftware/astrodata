"""Tests for the NIRI imaging mode.

.. _DRAGONS_NIRIIMG_TUTORIAL: https://dragons.readthedocs.io/\
projects/niriimg-drtutorial/en/v3.2.0/ex1_niriim_extended_dataset.html
"""

import glob
import importlib
import os

import pytest


from astrodata.testing import expand_file_range, download_multiple_files


@pytest.fixture(scope="session")
def niri_imaging_data_star_field_files():
    """Retrieve NIRI imaging data for the star field tutorial."""
    files = [
        "N20160102S0270-274",
        "N20160102S0275-279",
        "N20160102S0423-432",
        "N20160102S0373-382",
        "N20160102S0363-372",
        "N20160103S0463-472",
        "N20160102S0295-299",
        "bpm_20010317_niri_niri_11_full_1amp.fits",
    ]

    expanded_files = []

    for file in files:
        if not file.startswith("bpm"):
            expanded_files += expand_file_range(file)
            continue

        expanded_files += [file]

    return expanded_files


@pytest.fixture(scope="session")
def _downloaded_niri_imaging_data_star_field(
    tmpdir_factory, niri_imaging_data_star_field_files
):
    """Download NIRI imaging data for the star field tutorial."""
    tmpdir = tmpdir_factory.mktemp("niri_imaging_data_star_field")

    data = download_multiple_files(
        niri_imaging_data_star_field_files,
        path=tmpdir,
        sub_path="",
    )

    return data


@pytest.fixture
def niri_imaging_data_star_field(
    tmp_path, _downloaded_niri_imaging_data_star_field
):
    """This copies files from another fixture
    (_downloaded_niri_imaging_data_star_field), and copies those into a path
    for the current test.
    """
    # Copy the files from the temporary directory to the test directory instead
    # of re-downlaoding them.
    data = {}

    for file, path in _downloaded_niri_imaging_data_star_field.items():
        data[file] = tmp_path / file

        with open(data[file], "wb") as f:
            with open(path, "rb") as f2:
                f.write(f2.read())

    return data


@pytest.mark.dragons
def test_correct_astrodata():
    """Test if the astrodata package is being tested."""
    # Importing astrodata as if used with DRAGONS, instead of the top
    # import, for clarity/to test it explicitly.
    astrodata = importlib.import_module("astrodata")  # noqa: F811
    assert astrodata.from_file


@pytest.mark.filterwarnings("ignore:use 'astrodata.from_file'")
@pytest.mark.filterwarnings("ignore:Renamed to 'as_iraf_section'")
@pytest.mark.filterwarnings("ignore:Renamed to add_class")
@pytest.mark.filterwarnings("ignore:Renamed to 'windowed_operation'")
@pytest.mark.filterwarnings("ignore")
@pytest.mark.dragons
def test_niri_imaging_tutorial_star_field(
    use_temporary_working_directory,
    niri_imaging_data_star_field,
):
    """Test based on the DRAGONS NIRI imaging tutorial.

    This does **not** follow the tutorial directly. It is just testing based on
    the tutorial, and should be updated if the tutorial changes.

    Notably, importing is a bit different, and the tutorial uses a different
    method to get the data.

    Link: `DRAGONS_NIRIIMG_TUTORIAL`_
    """
    data = niri_imaging_data_star_field

    # Imports for running DRAGONS.
    # ruff: noqa: F841
    gemini_instruments = importlib.import_module("gemini_instruments")
    coreReduce = importlib.import_module("recipe_system.reduction.coreReduce")
    Reduce = coreReduce.Reduce
    dataselect = importlib.import_module("gempy.adlibrary.dataselect")
    cal_service = importlib.import_module("recipe_system.cal_service")

    all_files = sorted([str(path) for path in data.values()])

    # Use dataselect to sort data for reduction.
    darks = dataselect.select_data(
        all_files,
        ["DARK"],
        [],
    )

    darks_1_sec = dataselect.select_data(
        darks,
        [],
        [],
        dataselect.expr_parser("exposure_time==1"),
    )

    darks_20_sec = dataselect.select_data(
        darks,
        [],
        [],
        dataselect.expr_parser("exposure_time==20"),
    )

    flats = dataselect.select_data(
        all_files,
        ["FLAT"],
    )

    standard_stars = dataselect.select_data(
        all_files,
        [],
        [],
        dataselect.expr_parser('object=="FS 17"'),
    )

    science = dataselect.select_data(
        all_files,
        ["IMAGE"],
        ["FLAT"],
        dataselect.expr_parser('object!="FS 17"'),
    )

    # Initialize calibration service
    if os.path.exists("calibration.db"):
        os.remove("calibration.db")

    caldb = cal_service.LocalDB("calibration.db")
    caldb.init()

    # Darks
    reduce_darks = Reduce()
    reduce_darks.files.extend(darks_20_sec)
    reduce_darks.runr()

    # Using glob to ignore the metadata stuff in case of changes.
    assert os.path.exists("calibrations/processed_dark")
    processed_darks = glob.glob("calibrations/processed_dark/*")
    assert len(processed_darks) == 1, "Only one dark should be created."
    assert "crash" not in processed_darks[0], "Dark reduction failed."

    # Should also exist in the working directory
    cwd = os.getcwd()
    assert len(glob.glob("*dark*")) == 1, f"Darks not found in {cwd=}."

    # Add bad pixel masks to calibration service.
    for bpm in dataselect.select_data(all_files, ["BPM"]):
        caldb.add_cal(bpm)

    reduce_bpm = Reduce()
    reduce_bpm.files.extend(flats)
    reduce_bpm.files.extend(darks_1_sec)
    reduce_bpm.recipename = "makeProcessedBPM"
    reduce_bpm.runr()

    bpm = reduce_bpm.output_filenames[0]

    processed_bpms = glob.glob("*bpm*")
    assert len(processed_bpms) == 1, "Only one BPM should be created."
    assert "crash" not in processed_bpms[0], "BPM reduction failed."

    # Should also exist in the working directory
    cwd = os.getcwd()
    assert len(glob.glob("*bpm*")) == 1, f"BPM not found in {cwd=}."
    assert "crash" not in glob.glob("*bpm*")[0], "BPM reduction failed."

    # Flats
    reduce_flats = Reduce()
    reduce_flats.files.extend(flats)
    reduce_flats.uparms = [("addDQ:user_bpm", bpm)]
    reduce_flats.runr()

    processed_flat = glob.glob("calibrations/processed_flat/*")
    assert len(processed_flat) == 1, "Only one flat should be created."
    assert "crash" not in processed_flat[0], "Flat reduction failed."

    # Should also exist in the working directory
    cwd = os.getcwd()
    assert len(glob.glob("*flat*")) == 1, f"Flats not found in {cwd=}."
    assert "crash" not in glob.glob("*flat*")[0], "Flat reduction failed."

    # Standard star
    reduce_std = Reduce()
    reduce_std.files.extend(standard_stars)
    reduce_std.uparms = [("addDQ:user_bpm", bpm)]
    reduce_std.uparms.append(("darkCorrect:do_cal", "skip"))
    reduce_std.runr()

    # This creates one "_image" file
    processed_std_image = glob.glob("*_image*")

    assert len(processed_std_image) == 1, "Multiple standard star images."
    assert (
        "crash" not in processed_std_image[0]
    ), "Standard star reduction failed."

    # Science
    reduce_target = Reduce()
    reduce_target.files.extend(science)
    reduce_target.uparms = [("addDQ:user_bpm", bpm)]
    reduce_target.uparms.append(("skyCorrect:scale_sky", False))
    reduce_target.runr()

    processed_target_image = [
        x for x in glob.glob("*_image*") if x not in processed_std_image
    ]

    assert len(processed_target_image) == 1, "Multiple science images created."
    assert (
        "crash" not in processed_target_image[0]
    ), "Science reduction failed."

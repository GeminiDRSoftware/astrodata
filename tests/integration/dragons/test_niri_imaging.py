"""Tests for the NIRI imaging mode.

.. _DRAGONS_NIRIIMG_TUTORIAL: https://dragons.readthedocs.io/\
projects/niriimg-drtutorial/en/v3.2.0/ex1_niriim_extended_dataset.html
"""

import itertools
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
    tmp_path_factory, niri_imaging_data_star_field_files
):
    """Download NIRI imaging data for the star field tutorial."""
    tmpdir = tmp_path_factory.mktemp("niri_imaging_data_star_field")

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

    yield data

    print(f"Data located at: {tmp_path}")


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

    # Initialize calibration service
    if os.path.exists("calibration.db"):
        os.remove("calibration.db")

    caldb = cal_service.LocalDB("./calibration.db")
    caldb.init()

    # Use dataselect to sort data for reduction.
    all_files = sorted([str(path) for path in data.values()])

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

    # Make sure all files are available.
    for file in itertools.chain(darks, flats, standard_stars, science):
        assert file in all_files, f"File {file} not found."
        assert os.path.exists(file), f"File {file} not found."

    file_lists = {
        "darks_1_sec": darks_1_sec,
        "darks_20_sec": darks_20_sec,
        "flats": flats,
        "standard_stars": standard_stars,
        "science": science,
    }

    for name, file_list in file_lists.items():
        assert file_list, f"No {name} found."

    # Darks
    reduce_darks = Reduce()
    reduce_darks.files.extend(darks_20_sec)
    reduce_darks.runr()

    # Using glob to ignore the metadata stuff in case of changes.
    # Dark files should be in the working directory and in the calibrations
    # directory.
    dark_files = glob.glob("*dark*")
    calibration_darks = glob.glob("calibrations/processed_dark/*dark*")
    assert len(calibration_darks) == 1, "Expected 1 dark file."
    assert len(dark_files) == 1, "Expected 1 dark file."
    assert "crash" not in dark_files[0], "Dark reduction failed."

    # Add bad pixel masks to calibration service.
    for bpm in dataselect.select_data(all_files, ["BPM"]):
        caldb.add_cal(bpm)

    reduce_bpm = Reduce()
    reduce_bpm.files.extend(flats)
    reduce_bpm.files.extend(darks_1_sec)
    reduce_bpm.recipename = "makeProcessedBPM"
    reduce_bpm.runr()

    bpm = reduce_bpm.output_filenames[0]

    # Bpms should be in the working directory and in the calibrations directory.
    bpm_files = reduce_bpm.output_filenames
    assert len(bpm_files) == 1, f"Expected 1 bpm file. {bpm_files=}"
    assert "crash" not in bpm_files[0], "BPM reduction failed."

    # Flats
    reduce_flats = Reduce()
    reduce_flats.files.extend(flats)
    reduce_flats.uparms = [("addDQ:user_bpm", bpm)]
    reduce_flats.runr()

    # Flats should be in the working directory and in the calibrations directory.
    flat_files = glob.glob("*flat*")
    calibration_flats = glob.glob("calibrations/processed_flat/*flat*")
    assert len(calibration_flats) == 1, "Expected 1 flat file."
    assert len(flat_files) == 1, "Expected 1 flat file."
    assert "crash" not in flat_files[0], "Flat reduction failed."

    # Standard star
    reduce_std = Reduce()
    reduce_std.files.extend(standard_stars)
    reduce_std.uparms = [("addDQ:user_bpm", bpm)]
    reduce_std.uparms.append(("darkCorrect:do_cal", "skip"))
    reduce_std.runr()

    # This creates one "_image" file
    processed_std_image = glob.glob("*image*")

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
        x for x in glob.glob("*image*") if x not in processed_std_image
    ]

    assert len(processed_target_image) == 1, "Multiple science images created."
    assert (
        "crash" not in processed_target_image[0]
    ), "Science reduction failed."

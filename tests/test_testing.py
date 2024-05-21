"""Tests for the `astrodata.testing` module."""

import copy
import io
import itertools
import os
import pathlib
import warnings

import numpy as np
import pytest
import unittest
from hypothesis import given, strategies as st

import astrodata
import astrodata.testing as testing
from astrodata.testing import (
    assert_same_class,
    download_from_archive,
    skip_if_download_none,
)

from astropy.io import fits
from astropy.modeling import models, Model, Parameter


@pytest.fixture
def test_file_archive():
    return "N20180304S0126.fits"


@pytest.fixture
def ad1():
    file = astrodata.from_file(download_from_archive("N20180304S0126.fits"))

    assert file
    return file


@pytest.fixture
def ad2():
    file = astrodata.from_file(download_from_archive("N20180305S0001.fits"))

    assert file
    return file


def test_download_from_archive(monkeypatch, tmp_path):
    ncall = 0

    def mock_download(remote_url, **kwargs):
        nonlocal ncall
        ncall += 1
        fname = remote_url.split("/")[-1]
        # Create a fake file
        with open(os.path.join(tmp_path, fname), "w+") as _:
            pass

        return str(os.path.join(tmp_path, fname))

    env_var = "TEST_NEW_CACHE"
    monkeypatch.setenv(env_var, str(tmp_path))
    monkeypatch.setattr("astrodata.testing.download_file", mock_download)

    archive_filename = "THIS_IS_A_TEST.fits"

    # In case fname is not set, we need to set it to something that will fail
    fname = ".this_does_not_exist.fits"

    try:
        # first call will use our mock function above
        fname = astrodata.testing.download_from_archive(archive_filename)
        assert os.path.exists(fname)
        assert ncall == 1

        # second call will use the cache so we check that our mock function is not
        # called twice
        fname = astrodata.testing.download_from_archive(archive_filename)
        assert os.path.exists(fname)
        assert ncall == 1

    finally:
        # Clean up the downloaded file so the test works next time.
        if os.path.exists(fname):
            os.remove(fname)


@pytest.mark.skipif(os.name == "nt", reason="Test only works on unix/osx")
@skip_if_download_none
@pytest.mark.dragons_remote_data
def test_download_from_archive_raises_IOError_if_path_is_not_accessible():
    env_var = "MY_FAKE_ENV_VAR"
    os.environ["MY_FAKE_ENV_VAR"] = "/not/accessible/path"

    with pytest.raises(IOError):
        download_from_archive("N20180304S0126.fits", env_var=env_var)


def test_download_from_archive_raises_ValueError_if_envvar_does_not_exists():
    # This is slightly modified now to only check against environment variables
    # that cannot be assigned due to being things like empty strings or not
    # strings.
    with pytest.raises(ValueError):
        download_from_archive("N20180304S0126.fits", env_var="")

    with pytest.raises(ValueError):
        download_from_archive("N20180304S0126.fits", env_var=123)

    with pytest.raises(ValueError):
        download_from_archive("N20180304S0126.fits", env_var=None)

    with pytest.raises(ValueError):
        download_from_archive("N20180304S0126.fits", env_var="bing bong")


def test_download_from_archive_cannot_download_file(monkeypatch):
    def mock_download(remote_url, **kwargs):
        raise IOError("This is a test error.")

    monkeypatch.setattr("astrodata.testing.download_file", mock_download)

    testing.DownloadState().invalidate_cache()

    result = download_from_archive(
        "N20180304S0126.fits", cache=False, fail_on_error=False
    )

    assert result is None

    with pytest.raises(IOError):
        download_from_archive(
            "N20180304S0126.fits", cache=False, fail_on_error=True
        )

    testing.DownloadState().invalidate_cache()


def test_download_multiple_files(tmp_path, monkeypatch):
    # Create a fake download function that just creates a file.
    def mock_download(remote_url, **kwargs):
        fname = remote_url.split("/")[-1]
        with open(os.path.join(tmp_path, fname), "w+") as _:
            pass

        return str(os.path.join(tmp_path, fname))

    # Create a list of files to download.
    files = ["N20180304S0126.fits", "N20180305S0001.fits"]

    # Patch the download function.
    monkeypatch.setattr("astrodata.testing.download_file", mock_download)

    # Download the files.
    result = testing.download_multiple_files(files, path=tmp_path)

    # Check that the files were downloaded.
    for file in files:
        assert os.path.exists(result[file])

    # Check that the files were downloaded to the correct location.
    for file in files:
        assert result[file] == os.path.join(tmp_path, file)


def test_assert_most_close():
    from astrodata.testing import assert_most_close

    x = np.arange(10)
    y = np.arange(10)
    assert_most_close(x, y, 1)

    y[0] = -1
    assert_most_close(x, y, 1)

    with pytest.raises(AssertionError):
        y[1] = -1
        assert_most_close(x, y, 1)


def test_assert_most_equal():
    from astrodata.testing import assert_most_equal

    x = np.arange(10)
    y = np.arange(10)
    assert_most_equal(x, y, 1)

    y[0] = -1
    assert_most_equal(x, y, 1)

    with pytest.raises(AssertionError):
        y[1] = -1
        assert_most_equal(x, y, 1)


def test_assert_same_class():
    ad = astrodata.create({})
    ad2 = astrodata.create({})
    assert_same_class(ad, ad2)

    with pytest.raises(AssertionError):
        assert_same_class(ad, np.array([1]))


# Test fake_fits_bytes function.
def test_fake_fits_bytes():
    fake_fits_bytes = testing.fake_fits_bytes

    # Create a fake fits BytesIO stream.
    fake_fits = fake_fits_bytes()

    # Check that the fake fits is a BytesIO object.
    assert isinstance(fake_fits, io.BytesIO)

    # Check that the fake fits is a valid fits file.
    fake_fits.seek(0)

    # Creating a new bytes stream from the fake fits.
    str_data = io.BytesIO(fake_fits.read())
    str_data.seek(0)
    assert fits.getheader(str_data, 0)


def test_test_script_file(tmp_path):
    # Create a no-op test script file.
    noop_filename = os.path.join(tmp_path, "noop_test_script.py")
    ProcessError = testing.subprocess.CalledProcessError

    with open(noop_filename, "w+") as f:
        f.write("pass\n")

    # Check that the test script file is valid.
    assert testing.test_script_file(noop_filename, stdout_result="")

    # Create a failing test script file.
    failing_filename = os.path.join(tmp_path, "failing_test_script.py")

    with open(failing_filename, "w+") as f:
        f.write("assert False\n")

    # Check that the test script file is invalid.
    with pytest.raises(ProcessError):
        re_str = r"Traceback \((\w+\s*)*\w+\):.*AssertionError.*"

        testing.test_script_file(
            failing_filename,
            stdout_result="",
            stderr_result=re_str,
            fail_on_error=True,
        )

    # non-existing file
    non_existing_filename = os.path.join(tmp_path, "non_existing_file.py")
    with pytest.raises(FileNotFoundError):
        testing.test_script_file(non_existing_filename, stdout_result="")

    # Pass python options using argparse.
    python_script = r"""
    # This is a testing script that was originally a string literal.
    import argparse

    def cmdline():
        parser = argparse.ArgumentParser(description="Test script.")
        parser.add_argument("--option", type=str, default="default")
        args = parser.parse_args()
        print(args.option)

    if __name__ == "__main__":
        cmdline()
    """

    python_script = testing.process_string_to_python_script(python_script)

    python_script_filename = os.path.join(tmp_path, "python_script.py")

    with open(python_script_filename, "w+") as f:
        f.write(python_script)

    # Check that the test script file is valid.
    assert testing.test_script_file(
        python_script_filename,
        stdout_result="default",
    )


def _generate_permutations_with_strict_placement(
    shape: tuple[int],
) -> list[tuple[int]]:
    """Generate all permutations of a given shape with strict placement.

    This function generates all permutations of a given shape with strict placement.
    For example, if the shape is (2, 2), the function will return the following list:

    [
        (0, 0), (0, 1),
        (1, 0), (1, 1),
    ]

    Args:
        shape (tuple[int]): The shape to generate permutations for.

    Returns:
        list[tuple[int]]: A list of all permutations of the given shape with strict placement.
    """
    # Consumes the shape tuple to make sure it is a tuple.
    shape = tuple(x for x in shape)

    if not shape:
        return

    # This is by the function definition.
    if len(shape) == 1:
        return [(i,) for i in (0, shape[0] - 1)]

    # Generate all permutations of the shape with strict placement.
    def _get_other_perms(shape):
        if len(shape) == 1:
            return [(i,) for i in (0, shape[0] - 1)]

        perms = _get_other_perms(shape[1:])
        return [(i,) + p for i in (0, shape[0] - 1) for p in perms]

    return _get_other_perms(shape)


@pytest.mark.parametrize(
    "shape,corners_expected",
    (
        [
            tuple(x for x in shape),
            _generate_permutations_with_strict_placement(shape),
        ]
        for shape in itertools.chain(
            *[itertools.product(range(1, 6), repeat=i) for i in range(1, 5)]
        )
    ),
)
def test_get_corners(shape, corners_expected):
    corners = testing.get_corners(shape)

    assert len(corners) == 2 ** len(shape)
    assert sorted(corners_expected) == sorted(corners)


@pytest.mark.parametrize(
    "bad_input",
    (
        None,
        123,
        "string",
        [1, 2, 3],
        {},
        {"a": 1, "b": 2},
    ),
)
def test_get_corners_bad_input(bad_input):
    with pytest.raises(TypeError):
        testing.get_corners(bad_input)


def test_get_corners_empty_input():
    with pytest.raises(ValueError):
        testing.get_corners(())


class ExampleModel(Model):
    inputs = ("x",)
    outputs = ("y",)

    a = Parameter(default=0)
    b = Parameter(default=0)

    def evaluate(self, x):
        return self.a * x + self.b

    @property
    def n_inputs(self):
        return 1

    @property
    def n_outputs(self):
        return 1


_generic_example_model = ExampleModel(a=1, b=2)


@pytest.mark.parametrize(
    "model1,model2,expected",
    [
        (models.Gaussian1D(), models.Gaussian1D(), True),
        (models.Gaussian1D(), models.Gaussian2D(), False),
        (models.Gaussian1D(), models.Lorentz1D(), False),
        (models.Gaussian2D(), models.Lorentz1D(), False),
        (models.Gaussian1D(), models.Polynomial1D(1), False),
        (models.Gaussian1D(), models.Polynomial2D(1), False),
        (models.Gaussian1D(), models.Shift(), False),
        (ExampleModel(), ExampleModel(), True),
        (ExampleModel(), ExampleModel(a=1), False),
        (_generic_example_model, _generic_example_model, True),
        (_generic_example_model, ExampleModel(), False),
    ],
)
def test_compare_models(model1, model2, expected):
    if expected:
        testing.compare_models(model1, model2)
        return

    with pytest.raises(AssertionError):
        testing.compare_models(model1, model2)


_compare_model_bad_inputs = [
    st.integers(),
    st.floats(),
    st.lists(st.floats(), min_size=1, max_size=100),
    st.tuples(st.floats()),
    st.tuples(st.floats(), st.floats(), st.floats()),
    st.dictionaries(st.text(), st.floats()),
    st.dictionaries(st.integers(), st.floats()),
]


@given(
    a=st.one_of(_compare_model_bad_inputs),
    b=st.one_of(_compare_model_bad_inputs),
)
def test_compare_models_bad_input(a, b):
    with pytest.raises(TypeError):
        testing.compare_models(a, b)


def test_compare_models_bad_input_empty():
    with pytest.raises(TypeError):
        testing.compare_models((), ())


_non_func_strategies = [
    st.integers(),
    st.floats(),
    st.lists(st.floats(), min_size=1, max_size=100),
    st.tuples(st.floats()),
    st.tuples(st.floats(), st.floats(), st.floats()),
    st.dictionaries(st.text(), st.floats()),
    st.dictionaries(st.integers(), st.floats()),
    st.text(),
]


@given(bad_input=st.one_of(_non_func_strategies))
def test_skip_if_download_none_bad_input(bad_input):
    with pytest.raises(TypeError):
        skip_if_download_none(bad_input)


def raise_io_error(*args, **kwargs):
    raise IOError("This is a test error.")


@pytest.mark.parametrize(
    "download_func",
    [
        lambda *args, **kwargs: None,
        raise_io_error,
    ],
)
def test_skip_if_download_none_download_failure(monkeypatch, download_func):
    # Patch the download function.
    monkeypatch.setattr(
        "astrodata.testing.download_from_archive",
        download_func,
    )

    # Variable to check if the test function was called.
    _test_called = False

    # Invalidate the testing cache for this.
    testing.DownloadState().invalidate_cache()

    @skip_if_download_none
    def test_func():
        nonlocal _test_called
        _test_called = True

    with pytest.raises(unittest.SkipTest):
        test_func()

    # Check that the test function was skipped.
    assert not _test_called

    # Run the function again.
    with pytest.raises(unittest.SkipTest):
        test_func()

    # Check that the test function was skipped.
    assert not _test_called

    # Reset the DownloadState
    testing.DownloadState().invalidate_cache()


def test_warning_if_no_cache_path(monkeypatch):
    monkeypatch.delenv("ASTRODATA_TEST")

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        testing.download_from_archive(
            "N20180304S0126.fits", env_var="ASTRODATA_TEST"
        )

        assert len(w) == 1
        assert issubclass(w[-1].category, UserWarning)
        assert "ASTRODATA_TEST" in str(w[-1].message)


@pytest.mark.parametrize(
    "path,sub_path,expected_path",
    [
        ("test", "sub", "test/sub"),
        ("test", None, "test/raw_files"),
        (None, "sub", "cache_placeholder/sub"),
        (None, None, "cache_placeholder/raw_files"),
    ],
)
def test_download_file_path_subpath(
    monkeypatch,
    tmpdir,
    test_file_archive,
    path,
    sub_path,
    expected_path,
):
    # Change all paths to be pathlib.Path objects.
    tmpdir = pathlib.Path(tmpdir)
    path = pathlib.Path(path) if path is not None else None
    sub_path = pathlib.Path(sub_path) if sub_path is not None else None
    expected_path = pathlib.Path(expected_path)
    cache_path = os.path.join(str(tmpdir), "cache_placeholder")
    monkeypatch.setenv("ASTRODATA_TEST", cache_path)

    if path is not None:
        path = os.path.join(tmpdir, path)

    else:
        path = tmpdir

    if path == tmpdir:
        path = None

    if sub_path is not None:
        file_path = download_from_archive(
            test_file_archive, path=path, sub_path=sub_path, cache=False
        )

    else:
        file_path = download_from_archive(
            test_file_archive, path=path, cache=False
        )

    assert file_path == os.path.join(tmpdir, expected_path, test_file_archive)

    if path is not None:
        assert not os.path.exists(cache_path) or not os.listdir(cache_path)


def test_download_from_archive_None_sub_path(tmpdir, test_file_archive):
    # Test that the function works when sub_path is None.
    with pytest.warns(UserWarning) as record:
        file_path = download_from_archive(
            test_file_archive, path=tmpdir, sub_path=None, cache=False
        )

        assert file_path == os.path.join(tmpdir, test_file_archive)

    assert len(record) == 1, "Multiple warnings were raised."
    assert "sub_path" in str(
        record[0].message
    ), "Warning message does not contain sub_path."


@pytest.mark.parametrize(
    "bad_filename",
    [
        None,
        123,
        123.456,
        [1, 2, 3],
        {"a": 1, "b": 2},
        {"a", "b", "c"},
    ],
)
def test_download_bad_filename_type(tmpdir, bad_filename):
    # TODO: This is a generic exception, ideally it'd be a type error
    # explicitly.
    with pytest.raises(Exception):
        download_from_archive(bad_filename, path=tmpdir, cache=False)


@pytest.mark.parametrize(
    "bad_filename",
    [
        "file.fits",
        "file.txt",
        "not_never_ever_a_file.csv",
        "not_a_file.jpg",
        "not_a_file.png",
        "not_a_file.gif",
        "never_ever_not_never_existent_file.fits",
        "file/with/other/stuff.fits",
    ],
)
def test_download_raise_error_on_fail(tmpdir, bad_filename):
    with pytest.raises(IOError):
        download_from_archive(
            bad_filename,
            path=tmpdir,
            cache=False,
        )


def test_get_associated_calibrations(tmpdir, test_file_archive):
    associated_calibrations = testing.get_associated_calibrations(
        test_file_archive
    )

    results = associated_calibrations

    # TODO: Hardcoded expected values. Would be better to have a few cases to
    # test.
    assert len(results) == 13

    expected_filenames = [
        "N20180113S0131.fits",
        "N20180228S0213.fits",
        "N20180228S0214.fits",
        "N20180228S0215.fits",
        "N20180228S0216.fits",
        "N20180228S0217.fits",
        "N20180304S0121.fits",
        "N20180304S0124.fits",
        "N20180304S0125.fits",
        "N20180304S0126.fits",
        "N20180305S0099_bias.fits",
        "N20180525S0353.fits",
        "N20180820S0103.fits",
    ]

    result_filenames = [x["filename"] for x in associated_calibrations]

    assert sorted(result_filenames) == expected_filenames

    cal_types = {
        "N20180113S0131.fits": "specphot",
        "N20180228S0213.fits": "bias",
        "N20180228S0214.fits": "bias",
        "N20180228S0215.fits": "bias",
        "N20180228S0216.fits": "bias",
        "N20180228S0217.fits": "bias",
        "N20180304S0121.fits": "specphot",
        "N20180304S0124.fits": "specphot",
        "N20180304S0125.fits": "specphot",
        "N20180304S0126.fits": "flat",
        "N20180305S0099_bias.fits": "processed_bias",
        "N20180525S0353.fits": "arc",
        "N20180820S0103.fits": "spectwilight",
    }

    for cal in associated_calibrations:
        assert cal["caltype"] == cal_types[cal["filename"]]


def test_ADCompare_init(ad1, ad2):
    # Test that the ADCompare class is correctly initialized.
    compare = testing.ADCompare(ad1, ad2)

    assert compare.ad1 == ad1
    assert compare.ad2 == ad2

    with pytest.raises(AssertionError):
        compare.run_comparison()

    ad1_copy = copy.deepcopy(ad1)

    compare = testing.ADCompare(ad1, ad1_copy)

    assert compare.ad1 == ad1
    assert compare.ad2 == ad1_copy

    compare.run_comparison()


def test_ADCompare_run_comparison(ad1, ad2):
    ad3 = copy.deepcopy(ad1)
    ad3.phu.set("KEY", "VALUE")

    # Test ignoring keywords.abs
    compare = testing.ADCompare(ad1, ad3)

    # Check that ad1 and ad3 are not equal.
    with pytest.raises(AssertionError):
        compare.run_comparison()

    # Check that ad1 and ad3 are equal when ignoring keywords.
    keywords = {key for key in ad1.phu.keys()} | {
        key for key in ad3.phu.keys()
    }
    compare.run_comparison(ignore_kw=list(keywords))

    # Check that ad1 and ad2 are not equal.
    compare = testing.ADCompare(ad1, ad2)

    with pytest.raises(AssertionError):
        compare.run_comparison()

    # Check that ad1 and ad2 are also not equal when ignoring keywords.
    with pytest.raises(AssertionError):
        compare.run_comparison(ignore_kw=["KEY"])

    # Ignore a comparison
    ignore = ["filename"]

    ad3 = copy.deepcopy(ad1)
    ad3.filename = "[NOT THE SAME]"

    assert ad1.filename != ad3.filename

    with pytest.raises(AssertionError):
        compare = testing.ADCompare(ad1, ad3)
        compare.run_comparison()

    compare.run_comparison(ignore=set(ignore))

    # Ignore all comparisons
    # TODO: This should be more accessible/configurable.
    compare.run_comparison(
        ignore=[
            "filename",
            "tags",
            "numext",
            "refcat",
            "phu",
            "hdr",
            "attributes",
            "wcs",
        ]
    )


def test_ADCompare_numext(ad1, ad2):
    compare = testing.ADCompare(ad1, ad2)

    with pytest.raises(AssertionError):
        compare.run_comparison()

    # Check that the number of extensions is the same.
    ad2.append(ad2[0])

    assert compare.numext()

    def resize_ext(ad, n):
        while len(ad) < n:
            ad.append(ad[0])

        while len(ad) > n:
            ad = ad[:-1]

        return ad

    ad1, ad2 = (resize_ext(ad, 10) for ad in (ad1, ad2))

    compare = testing.ADCompare(ad1, ad2)

    assert not compare.numext()


def test_ADCompare_unequal_tags(ad1, tmp_path):
    # Get a file of a different type
    all_cals = testing.get_associated_calibrations("N20180304S0126.fits")

    # TODO this could just be a bias fixture and used elsewhere.
    all_cals = [cal for cal in all_cals if cal["caltype"] == "bias"]

    # Create two test classes that have different astrodata tags
    class TestAD1(astrodata.AstroData):
        @astrodata.astro_data_tag
        def tag1(self):
            return astrodata.TagSet(["TAG1"])

        @staticmethod
        def _matches_data(source):
            source = source.filename()
            source = os.path.basename(source)

            if source == all_cals[0]["filename"]:
                return True

            return False

    class TestAD2(astrodata.AstroData):
        @astrodata.astro_data_tag
        def tag2(self):
            return astrodata.TagSet(["TAG2"])

        @staticmethod
        def _matches_data(source):
            source = source.filename()
            source = os.path.basename(source)

            if source == all_cals[1]["filename"]:
                return True

            return False

    # Register our test classes
    astrodata.factory.add_class(TestAD1)
    astrodata.factory.add_class(TestAD2)

    # Downlaod the files
    file1 = download_from_archive(
        all_cals[0]["filename"],
        path=tmp_path,
        sub_path="",
        cache=False,
    )

    file2 = download_from_archive(
        all_cals[1]["filename"],
        path=tmp_path,
        sub_path="",
        cache=False,
    )

    # Load the two files
    ad1 = astrodata.from_file(file1)
    ad2 = astrodata.from_file(file2)

    assert all(isinstance(ad, astrodata.AstroData) for ad in (ad1, ad2))
    assert isinstance(ad1, TestAD1)
    assert isinstance(ad2, TestAD2)

    assert ad1.tags == {"TAG1"}
    assert ad2.tags == {"TAG2"}

    compare = testing.ADCompare(ad1, ad2)

    with pytest.raises(AssertionError):
        compare.run_comparison()

    assert compare.tags()

    # Create a third class that has the same tags as the first class, but
    # accepts the second file
    class TestAD3(astrodata.AstroData):
        @astrodata.astro_data_tag
        def tag2(self):
            return astrodata.TagSet(["TAG1"])

    astrodata.factory.remove_class(TestAD2)
    astrodata.factory.add_class(TestAD3)

    ad2 = astrodata.from_file(file2)

    assert isinstance(ad2, TestAD3)
    assert ad2.tags == {"TAG1"}

    compare = testing.ADCompare(ad1, ad2)

    assert not compare.tags()


def test_ADCompare_header_matching(ad1, ad2):
    ad2.hdr.remove("GAIN")

    compare = testing.ADCompare(ad1, ad2)

    with pytest.raises(AssertionError):
        compare.run_comparison()

    # Check that the headers are not the same.
    assert compare.hdr()

    # Check that the headers are the same when ignoring keywords.
    def get_all_keys(ad):
        headers = ad.hdr

        all_keys = set()

        for header in headers:
            all_keys |= set(header.keys())

        return all_keys

    all_keys = get_all_keys(ad1) | get_all_keys(ad2)

    with pytest.raises(AssertionError):
        compare.run_comparison(ignore_kw=list(all_keys))

    compare.ignore_kw = list(all_keys)

    assert not compare.hdr()


def test_ADCompare_header_matching_flip(ad1, ad2):
    ad2.hdr.remove("GAIN")

    compare = testing.ADCompare(ad1, ad2)

    with pytest.raises(AssertionError):
        compare.run_comparison()

    # Check that the headers are not the same.
    compare.ignore_kw = []
    assert compare.hdr()

    # Check that the headers are the same when ignoring keywords.
    def get_all_keys(ad):
        headers = ad.hdr

        all_keys = set()

        for header in headers:
            all_keys |= set(header.keys())

        return all_keys

    all_keys = get_all_keys(ad1) | get_all_keys(ad2)
    assert all_keys

    with pytest.raises(AssertionError):
        compare.run_comparison(ignore_kw=list(all_keys))

    compare.ignore_kw = list(all_keys)

    assert not compare.hdr()

    # Try the reverse order
    all_keys = get_all_keys(ad1) | get_all_keys(ad2)
    assert all_keys

    compare = testing.ADCompare(ad2, ad1)

    with pytest.raises(AssertionError):
        compare.run_comparison(ignore_kw=list(all_keys))

    compare.ignore_kw = list(all_keys)

    assert not compare.hdr()


def test_ADCompare_missing_refcat(ad1):
    """Test that ADCompare raises an error if a reference catalog is missing."""
    ad2 = copy.deepcopy(ad1)

    ad1.phu.REFCAT = ["test"]

    # Setting equal to None in this case is functionally equivalent to removing
    # the keyword.
    ad2.phu.REFCAT = None

    compare = testing.ADCompare(ad1, ad2)

    with pytest.raises(AssertionError):
        compare.run_comparison()

    assert compare.refcat()

    ad1.phu.REFCAT = None

    compare.run_comparison()
    assert not compare.refcat()

    ad1.phu.REFCAT = ["test"]
    ad2.phu.REFCAT = ["test"]

    compare.run_comparison()
    assert not compare.refcat()

    ad1.phu.REFCAT = ["test", "snudder thing"]

    compare = testing.ADCompare(ad1, ad2)

    with pytest.raises(AssertionError):
        compare.run_comparison()

    assert compare.refcat()


def test_ADCompare_wcs(ad1, ad2):
    ad1_copy = copy.deepcopy(ad1)
    ad2_copy = copy.deepcopy(ad2)

    compare = testing.ADCompare(ad1, ad2)

    with pytest.raises(AssertionError):
        compare.run_comparison()

    assert compare.wcs()

    ad1 = copy.deepcopy(ad1_copy)
    ad2 = copy.deepcopy(ad2_copy)


def test_ad_compare(ad1, ad2):
    assert testing.ad_compare(ad1, ad1)
    assert not testing.ad_compare(ad1, ad2)


@pytest.fixture
def file_ranges():
    """File ranges have the form "N3948493-503", for example."""
    range_expected = [
        (
            "N20170614S0201-205",
            [
                "N20170614S0201",
                "N20170614S0202",
                "N20170614S0203",
                "N20170614S0204",
                "N20170614S0205",
            ],
        ),
        (
            "N20170615S0534-538",
            [
                "N20170615S0534",
                "N20170615S0535",
                "N20170615S0536",
                "N20170615S0537",
                "N20170615S0538",
            ],
        ),
        (
            "N20170702S0178-182",
            [
                "N20170702S0178",
                "N20170702S0179",
                "N20170702S0180",
                "N20170702S0181",
                "N20170702S0182",
            ],
        ),
        (
            "N2093-2095",
            ["N2093", "N2094", "N2095"],
        ),
        (
            "N1-3",
            ["N1", "N2", "N3"],
        ),
        (
            "N1",
            ["N1"],
        ),
        (
            "N130987584759874984",
            ["N130987584759874984"],
        ),
        (
            "",
            [""],
        ),
    ]

    return range_expected


def test_expand_file_range(file_ranges):
    for file_range, expected in file_ranges:
        assert testing.expand_file_range(file_range) == expected

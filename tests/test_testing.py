"""Tests for the `astrodata.testing` module."""

import io
import itertools
import os

import numpy as np
import pytest

import astrodata
import astrodata.testing as testing
from astrodata.testing import (
    assert_same_class,
    download_from_archive,
    skip_if_download_none,
)

from astropy.io import fits


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
    shape: tuple[int]
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

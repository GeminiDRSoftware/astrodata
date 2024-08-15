# pragma: no cover
"""Define utility functions and classes for testing purposes."""

import enum
import functools
import io
import itertools
import logging
import os
import re
import shutil
import subprocess
import sys
import unittest
import urllib
import warnings
import xml.etree.ElementTree as et
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from typing import Iterable

import numpy as np
from astropy.io import fits
from astropy.table import Table
from astropy.utils.data import download_file

# Disable pylint import error
# pylint: disable=import-outside-toplevel

# from geminidr.gemini.lookups.timestamp_keywords import timestamp_keys
# from gempy.library import astrotools as at

GEMINI_ARCHIVE_URL = "https://archive.gemini.edu/file/"

# numpy random number generator for consistency.
_RANDOM_NUMBER_GEN = np.random.default_rng(42)

log = logging.getLogger(__name__)


class DownloadResult(enum.Enum):
    """Result status for the download_from_archive function.

    Enum class to store the possible states of the download_from_archive
    function. The states are used to determine if the function was successful
    in downloading a file from the archive.

    Attributes
    ----------
    SUCCESS : int
        The download was successful.

    NOT_FOUND : int
        The file was not found in the archive.

    NONE : int
        The state is not set.
    """

    SUCCESS = 2
    NOT_FOUND = 1
    NONE = 0


class DownloadState:
    """Stores the success state of the download_from_archive function.

    Singleton class to hold the state of the download_from_archive function.
    A bit of an annoying workaround because of conflicts with how ``pytest``'s
    fixtures work.

    The class is meant to be used as a singleton, so it should not be
    instantiated directly. Instead, the instance should be accessed via the
    ``_instance`` class attribute. Instantiation using ``DownloadState()`` will
    do this automatically.

    Attributes
    ----------
    _state : DownloadResult
        The state of the download_from_archive function.

    _valid_state : bool
        Flag to indicate if the state is valid.

    test_result : bool
        Result of the test download_from_archive function.

    Notes
    -----
    To check the state of the download_from_archive function, use the
    ``check_state`` method. This method will return the state of the function
    as a :class:`~DownloadResult` enum. If the state is not valid, the method
    will re-test the function.

    See the :class:`~DownloadResult` enum for the possible states and their
    documentation.
    """

    __slots__ = ["_state", "_valid_state", "test_result"]

    _instance = None

    def __new__(cls):
        """Instantiate or return the singleton class."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._state = None
            cls._instance._valid_state = False
            cls._instance.test_result = None

        return cls._instance

    def check_state(self) -> DownloadResult:
        """Check the state of the download_from_archive function."""
        SUCCESS = DownloadResult.SUCCESS
        NOT_FOUND = DownloadResult.NOT_FOUND
        NONE = DownloadResult.NONE

        if self._state is not NONE and self._valid_state:
            return self._state

        # Test if downloads are possible
        try:
            self.test_result = download_from_archive(
                "test.fits", cache=False, fail_on_error=True
            )

        except IOError:
            self._state = NOT_FOUND

        else:
            self._state = SUCCESS if self.test_result else NOT_FOUND

        self._valid_state = True
        return self._state

    def invalidate_cache(self):
        """Invalidate the cache of the download state."""
        self._valid_state = False


def skip_if_download_none(func):
    """Skip test if download_from_archive is returning None.

    Used as a wrapper for testing functions. Works with nose, pynose, and
    pytest.
    """
    if not callable(func):
        raise TypeError("Argument must be a callable")

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if DownloadState().check_state() is DownloadResult.NOT_FOUND:
            raise unittest.SkipTest(
                "Skipping test because download_from_archive returned None"
            )

        return func(*args, **kwargs)

    return wrapper


def get_corners(shape):
    """Calculate the corner indices of an array of the specified shape.

    This is a recursive function to calculate the corner indices
    of an array of the specified shape.

    Arguments
    ---------
    shape : tuple of ints
        Length of the dimensions of the array

    Taken directly from DRAGONS repository here:
    https://github.com/GeminiDRSoftware/DRAGONS
    (11/2/2023)

    This is required for a couple of the legacy tests.
    """
    if not isinstance(shape, tuple):
        raise TypeError("get_corners argument is non-tuple")

    if not shape:
        raise ValueError("get_corners argument is empty")

    if len(shape) == 1:
        corners = [(0,), (shape[0] - 1,)]
    else:
        size = len(shape)
        shape_less1 = shape[1:size]
        corners_less1 = get_corners(shape_less1)
        corners = []
        for corner in corners_less1:
            newcorner = (0,) + corner
            corners.append(newcorner)
            newcorner = (shape[0] - 1,) + corner
            corners.append(newcorner)

    return corners


def assert_most_close(
    actual,
    desired,
    max_miss,
    rtol=1e-7,
    atol=0,
    equal_nan=True,
    verbose=True,
):
    """Assert that two objects are equal up to a specified number of elements.

    Raises an AssertionError if the number of elements in two objects that
    are not equal up to desired tolerance is greater than expected.

    See Also
    --------
    :func:`~numpy.testing.assert_allclose`

    Arguments
    ---------
    actual : array_like
        Array obtained.

    desired : array_like
        Array desired.

    max_miss : iny
        Maximum number of mismatched elements.

    rtol : float, optional
        Relative tolerance.

    atol : float, optional
        Absolute tolerance.

    equal_nan : bool, optional.
        If True, NaNs will compare equal.

    verbose : bool, optional
        If True, the conflicting values are appended to the error message.

    Raises
    ------
    AssertionError
        If actual and desired are not equal up to specified precision.
    """
    from numpy.testing import assert_allclose

    try:
        assert_allclose(
            actual,
            desired,
            atol=atol,
            equal_nan=equal_nan,
            err_msg="",
            rtol=rtol,
            verbose=verbose,
        )

    except AssertionError as err:
        n_miss = (
            err.args[0]
            .split("\n")[3]
            .split(":")[-1]
            .split("(")[0]
            .split("/")[0]
        )
        n_miss = int(n_miss.strip())

        if n_miss > max_miss:
            error_message = (
                f"{n_miss} mismatching elements are more than the "
                + f"expected {max_miss}."
                + "\n".join(err.args[0].split("\n")[3:])
            )

            raise AssertionError(error_message) from err


def assert_most_equal(actual, desired, max_miss, verbose=True):
    """Assert that two objects are equal up to a specified number of elements.

    Raises an AssertionError if more than `n` elements in two objects are not
    equal. For more information, check :func:`numpy.testing.assert_equal`.

    Arguments
    ---------
    actual : array_like
        The object to check.

    desired : array_like
        The expected object.

    max_miss : int
        Maximum number of mismatched elements.

    verbose : bool, optional
        If True, the conflicting values are appended to the error message.

    Raises
    ------
    AssertionError
        If actual and desired are not equal.
    """
    # TODO(teald): Use importlib to import the necessary modules.
    from numpy.testing import assert_equal

    try:
        assert_equal(actual, desired, err_msg="", verbose=verbose)

    except AssertionError as err:
        n_miss = (
            err.args[0]
            .split("\n")[3]
            .split(":")[-1]
            .split("(")[0]
            .split("/")[0]
        )

        n_miss = int(n_miss.strip())

        if n_miss > max_miss:
            error_message = (
                f"{n_miss} mismatching elements are more than the "
                + f"expected {max_miss}."
                + "\n".join(err.args[0].split("\n")[3:])
            )

            raise AssertionError(error_message) from err


def assert_same_class(ad, ad_ref):
    """Compare two :class:`~astrodata.AstroData` objects have the same class.

    This function is used to compare two |AstroData| objects to ensure they are
    are equivalent classes, i.e., they are both |AstroData| objects or both
    |AstroData| subclasses.

    Arguments
    ----------
    ad : :class:`astrodata.AstroData` or any subclass
        AstroData object to be checked.

    ad_ref : :class:`astrodata.AstroData` or any subclass
        AstroData object used as reference
    """
    from astrodata import AstroData

    assert isinstance(ad, AstroData)
    assert isinstance(ad_ref, AstroData)
    assert isinstance(ad, type(ad_ref))


def compare_models(model1, model2, rtol=1e-7, atol=0.0, check_inverse=True):
    """Compare two models for similarity.

    Check that any two models are the same, within some tolerance on
    parameters (using the same defaults as numpy.assert_allclose()).

    This is constructed like a test, rather than returning True/False, in order
    to provide more useful information as to how the models differ when a test
    fails (and with more concise syntax).

    If `check_inverse` is True (the default), only first-level inverses are
    compared, to avoid unending recursion, since the inverse of an inverse
    should be the supplied input model, if defined. The types of any inverses
    (and their inverses in turn) are required to match whether or not their
    parameters etc. are compared.

    This function might not completely guarantee that model1 & model2 are
    identical for some models whose evaluation depends on class-specific
    parameters controlling how the array of model `parameters` is interpreted
    (eg. the orders in SIP?), but it does cover our common use of compound
    models involving orthonormal polynomials etc.

    Arguments
    ---------
    model1 : `astropy.modeling.Model`
        First model to compare.

    model2 : `astropy.modeling.Model`
        Second model to compare.

    rtol : float
        Relative tolerance.

    atol : float
        Absolute tolerance.

    check_inverse : bool
        If True, compare the inverses of the models as well.

    Raises
    ------
    AssertionError
        If the models are not the same.

    Notes
    -----
    This function is taken from the `DRAGONS` repository and is used to compare
    models in the context of the `DRAGONS` project. It is included here for
    completeness.
    """
    # TODO(teald): Use importlib to import the necessary modules.
    from astropy.modeling import Model
    from numpy.testing import assert_allclose

    if not (isinstance(model1, Model) and isinstance(model2, Model)):
        raise TypeError("Inputs must be Model instances")

    if model1 is model2:
        return

    # Require each model to be composed of same number of constituent models:
    assert model1.n_submodels == model2.n_submodels

    # Treat everything like an iterable compound model:
    if model1.n_submodels == 1:
        model1 = [model1]
        model2 = [model2]

    # Compare the constituent model definitions:
    for m1, m2 in zip(model1, model2):
        assert type(m1) is type(m2)
        assert len(m1.parameters) == len(m2.parameters)

        # NB. For 1D models the degrees match if the numbers of parameters do
        if hasattr(m1, "x_degree"):
            assert m1.x_degree == m2.x_degree

        if hasattr(m1, "y_degree"):
            assert m1.y_degree == m2.y_degree

        if hasattr(m1, "domain"):
            assert m1.domain == m2.domain

        if hasattr(m1, "x_domain"):
            assert m1.x_domain == m2.x_domain

        if hasattr(m1, "y_domain"):
            assert m1.y_domain == m2.y_domain

    # Return from lists if need be.
    if model1[0].n_submodels == 1 and len(model1) == 1:
        model1 = model1[0]
        model2 = model2[0]

    # Compare the model parameters (coefficients):
    assert_allclose(model1.parameters, model2.parameters, rtol=rtol, atol=atol)

    # Now check for any inverse models and require them both to have the same
    # type or be undefined:
    try:
        inverse1 = model1.inverse

    except NotImplementedError:
        inverse1 = None

    try:
        inverse2 = model2.inverse

    except NotImplementedError:
        inverse2 = None

    assert type(inverse1) is type(inverse2)

    # Compare inverses only if they exist and are not the forward model itself:
    if inverse1 is None or (inverse1 is model1 and inverse2 is model2):
        check_inverse = False

    # Recurse over the inverse models (but not their inverses in turn):
    if check_inverse:
        compare_models(
            inverse1, inverse2, rtol=rtol, atol=atol, check_inverse=False
        )


def download_multiple_files(
    files,
    path=None,
    sub_path="",
    use_threads=True,
    sequential=False,
    **kwargs,
):
    """Download multiple files from the archive and store them at a given path.

    Arguments
    ---------
    files : list of str
        List of filenames to download.

    path : str or os.PathLike or None
        Path to the cache directory. If None, the environment variable

    sub_path : str
        Sub-path to store the files. Default is "", which means the files are
        stored at the root of the cache directory (path kwarg).

    use_threads : bool
        If True, use threads to download the files in parallel. If False, use
        processes.

    sequential : bool
        If True, download the files sequentially. If False, download the files
        in parallel. This overrides the use_threads argument.

    kwargs : dict
        Additional keyword arguments to pass to
        :py:meth:`download_from_archive`.

    Returns
    -------
    dict
        Dictionary containing the downloaded files.
    """
    # Check if there are files to download
    if not files:
        return {}

    # Ensure the directory exists and is a directory
    if path is None:
        if env_var := kwargs.get("env_var", None) is not None:
            path = os.getenv(env_var)

        else:
            path = os.path.join(os.getcwd(), "_test_cache")
            warnings.warn(
                "Environment variable not set and no path provided, writing "
                f"to {path}. To suppress this warning, set the "
                "environment variable to the desired path for the "
                "testing cache."
            )

            # This is cleaned up once the program finishes.
            os.environ[env_var] = str(path)

    if not os.path.isdir(path) and os.path.exists(path):
        raise NotADirectoryError(f"{path} is not a directory")

    os.makedirs(path, exist_ok=True)

    # Download the files
    downloaded_files = {}

    if sequential:
        downloaded_files = {
            file: download_from_archive(
                file, path=path, sub_path=sub_path, **kwargs
            )
            for file in files
        }

        return downloaded_files

    executor_type = ThreadPoolExecutor if use_threads else ProcessPoolExecutor

    with executor_type() as executor:
        for file in files:
            downloaded_files[file] = executor.submit(
                download_from_archive,
                file,
                path=path,
                sub_path=sub_path,
                **kwargs,
            )

    downloaded_files = {
        file: future.result() for file, future in downloaded_files.items()
    }

    return downloaded_files


def download_from_archive(
    filename,
    path=None,
    sub_path="raw_files",
    env_var="ASTRODATA_TEST",
    cache=True,
    fail_on_error=True,
    suppress_stdout=False,
):
    """Download a file from the archive and store it in the local cache.

    Arguments
    ---------
    filename : str
        The filename, e.g. N20160524S0119.fits

    path : str or os.PathLike or None
        Path to the cache directory. If None, the environment variable
        ASTRODATA_TEST is used. otherwise, the file is saved to:
        os.path.join(path, sub_path, filename)

    sub_path : str
        By default the file is stored at the root of the cache directory, but
        using ``path`` allows to specify a sub-directory.

    env_var: str
        Environment variable containing the path to the cache directory.

    cache : bool
        If False, the file is downloaded and replaced in the cache directory.

    fail_on_error : bool
        If True, raise an error if the download fails. If False, return None.

    suppress_stdout : bool
        If True, suppress the output of the download command.

    Returns
    -------
    str
        Name of the cached file with the path added to it.
    """
    if sub_path is None:
        sub_path = ""
        warnings.warn(
            "sub_path is None, so the file will be saved to the root of the "
            "cache directory. To suppress this warning, set sub_path to a "
            "valid path (e.g., empty string instead of None)."
        )

    # Check that the environment variable is a valid name.
    if not isinstance(env_var, str) or not env_var.isidentifier():
        raise ValueError(f"Environment variable name is not valid: {env_var}")

    # Find cache path and make sure it exists
    root_cache_path = os.getenv(env_var)

    if root_cache_path is None:
        if path is not None:
            root_cache_path = os.path.expanduser(path)

        else:
            root_cache_path = os.path.join(os.getcwd(), "_test_cache")
            warnings.warn(
                f"Environment variable not set: {env_var}, writing "
                f"to {root_cache_path}. To suppress this warning, set "
                f"the environment variable {env_var} to the desired path "
                f"for the testing cache."
            )

            # This is cleaned up once the program finishes.
            os.environ[env_var] = str(root_cache_path)

    root_cache_path = os.path.expanduser(root_cache_path)

    if path is None:
        path = root_cache_path

    cache_path = os.path.join(os.path.expanduser(path), sub_path)

    if not os.path.exists(cache_path):
        os.makedirs(cache_path)

    # Now check if the local file exists and download if not
    try:
        local_path = os.path.join(cache_path, filename)
        url = GEMINI_ARCHIVE_URL + filename

        if cache and os.path.exists(local_path):
            # Use the cached file
            return local_path

        # Use a context that suppresses the output of the download command
        with open(os.devnull, "w") as devnull:
            stdout_prev = sys.stdout

            if suppress_stdout:
                sys.stdout = devnull

            try:
                tmp_path = download_file(url, cache=False)

            finally:
                sys.stdout = stdout_prev

        shutil.move(tmp_path, local_path)

        # `download_file` ignores Access Control List - fixing it
        os.chmod(local_path, 0o664)

    except Exception as err:
        if not fail_on_error:
            log.debug(f"Failed to download {filename} from the archive")
            log.debug(f" - Error: {err}")
            return None

        raise IOError(
            f"Failed to download {filename} from the archive ({url})"
        ) from err

    return local_path


def get_associated_calibrations(filename, nbias=5):
    """Query Gemini Observatory Archive for associated calibrations.

    This function quieries the Gemini Observatory Archive for calibrations
    associated with a given data file.

    Arguments
    ---------
    filename : str
        Input file name
    """
    url = f"https://archive.gemini.edu/calmgr/{filename}"
    tree = et.parse(urllib.request.urlopen(url))
    root = tree.getroot()
    prefix = root.tag[: root.tag.rfind("}") + 1]

    rows = []
    for node in tree.iter(prefix + "calibration"):
        cal_type = node.find(prefix + "caltype").text
        cal_filename = node.find(prefix + "filename").text
        if not ("processed_" in cal_filename or "specphot" in cal_filename):
            rows.append((cal_filename, cal_type))

    tbl = Table(rows=rows, names=["filename", "caltype"])
    tbl.sort("filename")
    tbl.remove_rows(np.where(tbl["caltype"] == "bias")[0][nbias:])
    return tbl


class ADCompare:
    """Compare two |AstroData| instances for near-equality.

    Use this class to determine whether two |AstroData| instances are basically
    the same. Various properties (both data and metadata) can be compared
    """

    # These are the keywords relating to a FITS WCS that we won't check
    # because we check the gWCS objects instead
    fits_keys = set(["WCSAXES", "WCSDIM", "RADESYS", "BITPIX"])
    for i in range(1, 6):
        fits_keys.update(
            [f"CUNIT{i}", f"CTYPE{i}", f"CDELT{i}", f"CRVAL{i}", f"CRPIX{i}"]
        )
    fits_keys.update([f"CD{i}_{j}" for i in range(1, 6) for j in range(1, 6)])

    def __init__(self, ad1, ad2):
        self.ad1 = ad1
        self.ad2 = ad2

        self.max_miss = None
        self.rtol = None
        self.atol = None
        self.ignore_kw = None

    def run_comparison(
        self,
        max_miss=0,
        rtol=1e-7,
        atol=0,
        compare=None,
        ignore=None,
        ignore_fits_wcs=True,
        ignore_kw=None,
        raise_exception=True,
    ):
        """Perform a comparison between the two AD objects in this instance.

        Arguments
        ---------
        max_miss: int
            maximum number of elements in each array that can disagree

        rtol: float
            relative tolerance allowed between array elements

        atol: float
            absolute tolerance allowed between array elements

        compare: list/None
            list of comparisons to perform

        ignore: list/None
            list of comparisons to ignore

        ignore_fits_wcs: bool
            ignore FITS keywords relating to WCS (to allow a comparison
            between an in-memory AD and one on disk if you're not interested
            in these, without needed to save to disk)

        ignore_kw: sequence/None
            additional keywords to ignore in headers

        raise_exception: bool
            raise an AssertionError if the comparison fails? If False,
            the errordict is returned, which may be useful if a very
            specific mismatch is permitted

        Raises
        ------
        AssertionError if the AD objects do not agree.
        """
        self.max_miss = max_miss
        self.rtol = rtol
        self.atol = atol
        self.ignore_kw = self.fits_keys if ignore_fits_wcs else set([])

        if ignore_kw:
            self.ignore_kw.update(ignore_kw)

        if compare is None:
            compare = (
                "filename",
                "tags",
                "numext",
                "refcat",
                "phu",
                "hdr",
                "attributes",
                "wcs",
            )

        if ignore is not None:
            compare = [c for c in compare if c not in ignore]

        errordict = {}
        for func_name in compare:
            errorlist = getattr(self, func_name)()
            if errorlist:
                errordict[func_name] = errorlist

        if errordict and raise_exception:
            raise AssertionError(self.format_errordict(errordict))

        return errordict

    def numext(self):
        """Check the number of extensions is equal."""
        numext1, numext2 = len(self.ad1), len(self.ad2)
        if numext1 != numext2:
            return [f"{numext1} v {numext2}"]

        return []

    def filename(self):
        """Check the filenames are equal."""
        fname1, fname2 = self.ad1.filename, self.ad2.filename

        if fname1 != fname2:
            return [f"{fname1} v {fname2}"]

        return []

    def tags(self):
        """Check the tags are equal."""
        tags1, tags2 = self.ad1.tags, self.ad2.tags

        if tags1 != tags2:
            return [f"{tags1}\n  v {tags2}"]

        return []

    def phu(self):
        """Check the PHUs agree."""
        # Ignore NEXTEND as only recently added and len(ad) handles it
        errorlist = self._header(
            self.ad1.phu,
            self.ad2.phu,
            ignore=self.ignore_kw.union({"NEXTEND"}),
        )

        return errorlist

    def hdr(self):
        """Check the extension headers agree."""
        errorlist = []
        for i, (hdr1, hdr2) in enumerate(zip(self.ad1.hdr, self.ad2.hdr)):
            elist = self._header(hdr1, hdr2, ignore=self.ignore_kw)
            if elist:
                errorlist.extend([f"Slice {i} HDR mismatch"] + elist)
        return errorlist

    def _header(self, hdr1, hdr2, ignore=None):
        """Compare headers, ignoring keywords in ignore.

        Arguments
        ---------
        hdr1 : Header
            First header to compare.

        hdr2 : Header
            Second header to compare.

        ignore : list
            List of keywords to ignore during comparison.
        """
        errorlist = []
        s1 = set(hdr1.keys()) - {"HISTORY", "COMMENT"}
        s2 = set(hdr2.keys()) - {"HISTORY", "COMMENT"}
        if ignore:
            s1 -= set(ignore)
            s2 -= set(ignore)
        if s1 != s2:
            if s1 - s2:
                errorlist.append(f"Header 1 contains keywords {s1 - s2}")
            if s2 - s1:
                errorlist.append(f"Header 2 contains keywords {s2 - s1}")

        # If present, import timestamp_keys from geminidr.gemini.lookups
        # to compare the timestamps in the headers.
        try:
            from geminidr.gemini.lookups.timestamp_keywords import (
                timestamp_keys,
            )

        except ImportError:
            timestamp_keys = {}

        for kw in hdr1:
            # GEM-TLM is "time last modified"
            if (
                kw not in timestamp_keys.values()
                and kw not in ["GEM-TLM", "HISTORY", "COMMENT", ""]
                and kw not in self.ignore_kw
            ):
                try:
                    v1, v2 = hdr1[kw], hdr2[kw]

                except KeyError:  # Missing keyword in AD2
                    continue

                try:
                    if abs(v1 - v2) >= 0.01:
                        errorlist.append(f"{kw} value mismatch: {v1} v {v2}")

                except TypeError:
                    if v1 != v2:
                        errorlist.append(f"{kw} value inequality: {v1} v {v2}")

        return errorlist

    def refcat(self):
        """Check both ADs have REFCATs (or not) and their lengths agree."""
        # REFCAT can be in the PHU or the AD itself, depending on if REFCAT is
        # implemented as a property/attr or not in the parent class.
        refcat1 = getattr(self.ad1.phu, "REFCAT", None)
        refcat2 = getattr(self.ad2.phu, "REFCAT", None)

        # Check if only one is missing
        if (refcat1 is None) ^ (refcat2 is None):
            return [f"presence: {refcat1 is not None} v {refcat2 is not None}"]

        # Match the lengths
        if refcat1 is not None:  # and refcat2 must also exist
            len1, len2 = len(refcat1), len(refcat2)
            if len1 != len2:
                return [f"lengths: {len1} v {len2}"]

        # TODO: Should we check the contents of the REFCATs? Or is that checked
        # elsewhere/by some other method/equality impl?

        return []

    def attributes(self):
        """Check extension-level attributes."""
        errorlist = []
        for i, (ext1, ext2) in enumerate(zip(self.ad1, self.ad2)):
            elist = self._attributes(ext1, ext2)
            if elist:
                errorlist.extend([f"Slice {i} attribute mismatch"] + elist)
        return errorlist

    def _attributes(self, ext1, ext2):
        """Check the attributes of two extensions."""
        errorlist = []
        for attr in ["data", "mask", "variance", "OBJMASK", "OBJCAT"]:
            attr1 = getattr(ext1, attr, None)
            attr2 = getattr(ext2, attr, None)

            if all(attr is None for attr in [attr1, attr2]):
                continue

            if not np.array_equal(attr1, attr2):
                errorlist.append(f"{attr} mismatch: {attr1} v {attr2}")
                continue

        return errorlist

    def wcs(self):
        """Check WCS agrees between ad objects."""

        def compare_frames(frame1, frame2):
            """Compare the important stuff of two CoordinateFrame instances."""
            for attr in (
                "naxes",
                "axes_type",
                "axes_order",
                "unit",
                "axes_names",
            ):
                assert getattr(frame1, attr) == getattr(frame2, attr)

        errorlist = []
        for i, (ext1, ext2) in enumerate(zip(self.ad1, self.ad2)):
            wcs1, wcs2 = ext1.wcs, ext2.wcs
            if (wcs1 is None) != (wcs2 is None):
                errorlist.append(
                    f"Slice {i} WCS presence mismatch "
                    f"{wcs1 is not None} {wcs2 is not None}"
                )
                continue

            if wcs1 is None:  # and wcs2 is also None
                continue

            frames1, frames2 = wcs1.available_frames, wcs2.available_frames

            if frames1 != frames2:
                errorlist.append(
                    f"Slice {i} frames differ: {frames1} v {frames2}"
                )
                return errorlist

            for frame in frames1:
                frame1, frame2 = getattr(wcs1, frame), getattr(wcs2, frame)
                try:
                    compare_frames(frame1, frame2)

                except AssertionError:
                    errorlist.compare(
                        f"Slice {i} {frame} differs: " f"{frame1} v {frame2}"
                    )

            corners = get_corners(ext1.shape)
            world1, world2 = wcs1(*zip(*corners)), wcs2(*zip(*corners))

            try:
                np.testing.assert_allclose(world1, world2)

            except AssertionError:
                errorlist.append(
                    f"Slice {i} world coords differ: {world1} v {world2}"
                )

        return errorlist

    def format_errordict(self, errordict):
        """Format the errordict into a str for reporting."""
        errormsg = (
            f"Comparison between {self.ad1.filename} and {self.ad2.filename}"
        )
        for k, v in errordict.items():
            errormsg += f"\nComparison failure in {k}"
            errormsg += "\n" + ("-" * (22 + len(k))) + "\n"
            errormsg += "\n  ".join(v)
        return errormsg


def ad_compare(ad1, ad2, **kwargs):
    """Compare the tags, headers, and pixel values of two images.

    This is a wrapper for ADCompare.run_comparison() for
    backward-compatibility.

    Arguments
    ---------
    ad1: AstroData
        first AD objects

    ad2: AstroData
        second AD object

    Returns
    -------
    bool: are the two AD instances basically the same?
    """
    try:
        ADCompare(ad1, ad2).run_comparison(**kwargs)

    except AssertionError:
        return False

    return True


_HDUL_LIKE_TYPE = fits.HDUList | list[fits.hdu.FitsHDU]


def fake_fits_bytes(
    hdus: _HDUL_LIKE_TYPE | None = None,
    n_extensions: int = 0,
    image_shape: tuple[int, int] | None = None,
    include_header_keys: Iterable[str] | dict[str, str] | None = None,
    include_header_values: dict[str, str] | None = None,
    masks: bool = False,
    single_hdu: bool = False,
) -> io.BytesIO:
    """Create a fake FITS file in memory and return readable BytesIO object.

    Arguments
    ---------
    hdus : HDUList | list[HDUBase] | None
        The HDUList or list of HDUBase objects to be written to the file.  If
        None, a file with a primary HDU and n_extension extension HDUs are
        generated.

    n_extensions : int
        The number of extension HDUs to be created if hdus is None.
        Default is 0 (primary HDU alone)

    image_shape : tuple[int, int] | None
        The shape of the image to be created in the primary HDU. If None, no
        image is created.

    include_header_keys : Iterable[str] | dict[str, str] None
        A list of header keywords to be included in the primary HDU. If None,
        no header keywords are included.

    include_header_values : dict[str, str] | None
        A dictionary of header keywords and values to be included in the
        primary HDU. If None, no header keywords are included.

    masks : bool
        If True, a mask is created for the primary HDU or the image extensions.

    single_hdu : bool
        If True, only the primary HDU is created. If False, the primary HDU and
        n_extensions are created.
    """
    # Because of peculiarities with pytest, fits imports are done inside the
    # function.
    from astropy.io import fits

    # If HDUs are provided, other arguments (other than n_extensions) should
    # raise an error.
    if hdus is not None and any(
        (image_shape, include_header_keys, single_hdu)
    ):
        warnings.warn(
            "Arguments image_shape and include_header_keys are ignored when "
            "hdus is provided."
        )

    image_shape = image_shape or (100, 100)

    # If mask is True, a mask is created for the primary HDU or the image
    # extensions. Creating a generic mask with some non-zero values.
    if masks:
        min_choice, max_choice = 0, 64

        mask = _RANDOM_NUMBER_GEN.integers(
            min_choice,
            max_choice,
            size=image_shape,
            dtype=np.uint16,
        )

        # Setting some random pixels to zero on the mask
        good_values = _RANDOM_NUMBER_GEN.random(mask.shape) > 0.25
        mask[good_values] = 0

    # Only one file type (fits) is supported at the moment. Eventually this
    # will be factored out into its own function.
    if hdus is None:
        primary_hdu = fits.PrimaryHDU(data=np.zeros(image_shape))

        if include_header_keys is not None and not isinstance(
            include_header_keys, dict
        ):
            for key in include_header_keys:
                if key in include_header_values:
                    primary_hdu.header[key] = include_header_values[key]
                    continue

                primary_hdu.header[key] = "TEST_VALUE"

        elif (
            not isinstance(include_header_keys, dict)
            and include_header_values is not None
        ):
            for key, value in zip(include_header_keys, include_header_values):
                primary_hdu.header[key] = value

        elif (
            isinstance(include_header_keys, dict) and not include_header_values
        ):
            for key, value in include_header_keys.items():
                primary_hdu.header[key] = value

        elif all(
            x is None for x in (include_header_keys, include_header_values)
        ):
            # Just a primary HDU with no header keywords
            pass

        else:
            raise ValueError(
                f"Could not create header from include_header_keys: "
                f"{include_header_keys} and include_header_values: "
                f"{include_header_values}. NOTE: include_header_keys "
                f"should be None if include_header_values is a dictionary."
            )

        if single_hdu or not n_extensions:
            if n_extensions:
                raise ValueError(
                    "n_extensions must be 0 (default) if single_hdu is "
                    "True and hdus is None."
                )

            hdus = primary_hdu

            if masks:
                raise NotImplementedError

        else:
            hdus = [primary_hdu]

            for i in range(n_extensions):
                image = fits.ImageHDU(np.ones(image_shape))
                image.header["EXTNAME"] = "SCI"
                image.header["EXTVER"] = i + 1

                hdus.append(image)

                if masks:
                    mask_image = fits.ImageHDU(np.copy(mask), name="mask")
                    mask_image.header["EXTNAME"] = "mask"
                    mask_image.header["EXTVER"] = i + 1

                    hdus.append(mask_image)

    file_data = io.BytesIO()

    if single_hdu:
        hdus.writeto(file_data)

    else:
        hdus = fits.HDUList(hdus)
        hdus.writeto(file_data)

    file_data.seek(0)

    return file_data


def test_script_file(
    script_path: os.PathLike | str,
    stdout_result: str | None = None,
    stderr_result: str | None = None,
    python_options: str | list[str] = "",
    script_options: str | list[str] = "",
    fail_on_error: bool = True,
    break_after_run: bool = False,
    regex_options: re.RegexFlag = re.MULTILINE | re.DOTALL,
) -> bool:
    """Run a script file and check the output.

    All matches (i.e., stdout_result and stderr_result) can use regular
    expressions.

    Arguments
    ---------
    script_path : str
        The path to the script to be run.

    stdout_result : str | None
        The expected result from the standard output. If None, the standard
        output is not checked.

    stderr_result : str | None
        The expected result from the standard error. If None, the standard
        error is not checked.

    python_options : str | list[str]
        Options to be passed to the python interpreter when running the script.

    script_options : str | list[str]
        Options to be passed to the script when running it.

    fail_on_error : bool
        If True, an AssertionError is raised if the output does not match the
        expected results.

    break_after_run : bool
        If True, the script will pause at the end before closing, and escape
        using the built-in `breakpoint()` function.

    regex_options : re.RegexFlag
        The regular expression flags to be used when matching the output.
        The default is re.MULTILINE | re.DOTALL.

    Returns
    -------
    bool
        True if the output matches the expected results.

    Raises
    ------
    FileNotFoundError
        If the script file is not found.

    subprocess.CalledProcessError
        If the script returns a non-zero exit code.

    AssertionError
        If the output does not match the expected results.

    Notes
    -----
    The script is run using the python interpreter, so the script file should
    have a shebang line at the top to specify the interpreter to be used. This
    isn't an issue for most scripts, but it is something to be aware of if you
    are expecting to use/test with a sepcific interpreter.
    """
    if not os.path.exists(script_path):
        raise FileNotFoundError(f"Script file {script_path} not found.")

    if isinstance(python_options, str):
        python_options = python_options.split()

    command_components = [
        ["python"],
        python_options,
        [script_path],
        script_options,
    ]

    command = [x for x in itertools.chain(*command_components)]

    process = subprocess.run(
        command,
        capture_output=True,
    )

    stdout = process.stdout
    stderr = process.stderr

    # Helper function to check the output against the expected results using
    # regex.
    def _reg_assert(result, expected):
        match = re.match(expected, result, flags=regex_options)

        if not match:
            raise AssertionError(
                f"Expected pattern {expected!r} but got:\n{result!r}"
            )

    if stdout_result is not None:
        _reg_assert(stdout.decode("utf-8"), stdout_result)

    if stderr_result is not None:
        _reg_assert(stderr.decode("utf-8"), stderr_result)

    if fail_on_error and process.returncode:
        raise subprocess.CalledProcessError(
            process.returncode, command, stdout, stderr
        )

    return True


def process_string_to_python_script(string: str) -> str:
    """Format a stirng to be used as a Python script.

    Arguments
    ---------
    string : str
        The string to be processed.
    """
    # For multiline strings, need to get rid of possible hanging indents
    # The first line may be unindented.
    lines = string.split("\n")
    first_line = lines[0].strip()

    # Determine the minimum indentation of the other lines.
    min_indent = min(
        len(line) - len(line.lstrip()) for line in lines[1:] if line.strip()
    )

    # Remove the minimum indentation from all lines.
    lines = [first_line] + [line[min_indent:] for line in lines[1:]]

    return "\n".join(lines)


def get_program_observations():
    """Get the program and observation IDs for the current test.

    .. warning::
        This function is not implemented. It will be implemented in a future
        release.
    """
    raise NotImplementedError


def expand_file_range(files: str) -> list[str]:
    """Expand a range of files into a list of file names.

    Arguments
    ---------
    files : str
        A range of files, e.g., "N20170614S0201-205". This would produce:

        ["N20170614S0201", "N20170614S0202", ..., "N20170614S0205"]

    Returns
    -------
    list[str]
        A list of file names.
    """
    if "-" in files:
        file_prep, end = files.split("-")
        file_prep, start = file_prep[: -len(end)], file_prep[-len(end) :]
        start, end = int(start), int(end)
        files = [
            f"{file_prep}{str(i).zfill(len(str(end)))}"
            for i in range(start, end + 1)
        ]

        return files

    return [files]

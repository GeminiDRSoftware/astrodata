"""Functions used when interacting with FITS files and HDUs.

.. |NDData| replace:: :class:`~astropy.nddata.NDData`
.. |NDDataRef| replace:: :class:`~astropy.nddata.NDDataRef`
.. |BinTableHDU| replace:: :class:`~astropy.io.fits.BinTableHDU`
.. |TableHDU| replace:: :class:`~astropy.io.fits.TableHDU`
.. |NDAstroData| replace:: :class:`~astrodata.nddata.NDAstroData`
.. |NDAstroDataRef| replace:: :class:`~astrodata.nddata.NDAstroDataRef`
"""
from collections import OrderedDict
from copy import deepcopy
from io import BytesIO
from itertools import product as cart_product, zip_longest
import gc
import logging
import os
import traceback
import warnings

from astropy import units as u
from astropy.io import fits
from astropy.io.fits import (
    BinTableHDU,
    Column,
    DELAYED,
    HDUList,
    ImageHDU,
    PrimaryHDU,
    TableHDU,
)
from astropy.nddata import NDData

# NDDataRef is still not in the stable astropy, but this should be the one
# we use in the future...
# from astropy.nddata import NDData, NDDataRef as NDDataObject
from astropy.table import Table

import asdf
import astropy
import jsonschema
import numpy as np


from gwcs.wcs import WCS as gWCS

from .nddata import ADVarianceUncertainty, NDAstroData
from .utils import deprecated
from .wcs import fitswcs_to_gwcs, gwcs_to_fits

DEFAULT_EXTENSION = "SCI"
NO_DEFAULT = object()
LOGGER = logging.getLogger(__name__)


class FitsHeaderCollection:
    """Group access to a list of FITS Header-like objects.

    It exposes a number of methods (``set``, ``get``, etc.) that operate over
    all the headers at the same time. It can also be iterated.

    Parameters
    ----------
    headers : list of `astropy.io.fits.Header`
        List of Header objects.
    """

    def __init__(self, headers):
        self._headers = list(headers)

    def _insert(self, idx, header):
        self._headers.insert(idx, header)

    def __iter__(self):
        yield from self._headers

    def __setitem__(self, key, value):
        if isinstance(value, tuple):
            self.set(key, value=value[0], comment=value[1])
        else:
            self.set(key, value=value)

    def set(self, key, value=None, comment=None):
        """Set a keyword in all the headers."""
        for header in self._headers:
            header.set(key, value=value, comment=comment)

    def __getitem__(self, key):
        missing_at = []
        ret = []
        for n, header in enumerate(self._headers):
            try:
                ret.append(header[key])

            except KeyError:
                logging.debug(
                    "Assigning None to header missing keyword %s", key
                )

                missing_at.append(n)
                ret.append(None)

        if missing_at:
            error = KeyError(
                f"The keyword couldn't be found at headers: "
                f"{tuple(missing_at)}"
            )

            error.missing_at = missing_at
            error.values = ret
            raise error

        return ret

    def get(self, key, default=None):
        """Get a keyword, defaulting to None."""
        try:
            return self[key]
        except KeyError as err:
            vals = err.values
            for n in err.missing_at:
                vals[n] = default
            return vals

    def __delitem__(self, key):
        self.remove(key)

    def remove(self, key):
        """Remove a keyword from all the headers."""
        deleted = 0
        for header in self._headers:
            try:
                del header[key]
                deleted = deleted + 1
            except KeyError:
                pass
        if not deleted:
            raise KeyError(f"'{key}' is not on any of the extensions")

    def get_comment(self, key):
        """Get the comment for a keyword, from all the headers, as a list."""
        return [header.comments[key] for header in self._headers]

    def set_comment(self, key, comment):
        """Set the comment for a keyword in all the headers."""

        def _inner_set_comment(header):
            if key not in header:
                raise KeyError(f"Keyword {key!r} not available")

            header.set(key, comment=comment)

        for n, header in enumerate(self._headers):
            try:
                _inner_set_comment(header)
            except KeyError as err:
                raise KeyError(f"{err.args[0]} at header {n}") from err

    def __contains__(self, key):
        return any(tuple(key in h for h in self._headers))


def new_imagehdu(data, header, name=None):
    """Create a new ImageHDU from data and header.

    Parameters
    ----------
    data : `numpy.ndarray`
        The data array.

    header : `astropy.io.fits.Header`
        The header.

    name : str
        The extension name.

    Notes
    -----
    Assigning data in a delayed way, won't reset BZERO/BSCALE in the header,
    for some reason. Need to investigated. Maybe astropy.io.fits bug. Figure
    out WHY were we delaying in the first place.

    Example:
    >> i = ImageHDU(data=DELAYED, header=header.copy(), name=name)
    >> i.data = data
    """
    # Assigning data in a delayed way, won't reset BZERO/BSCALE in the header,
    # for some reason. Need to investigated. Maybe astropy.io.fits bug. Figure
    # out WHY were we delaying in the first place.
    #    i = ImageHDU(data=DELAYED, header=header.copy(), name=name)
    #    i.data = data
    return ImageHDU(data=data, header=header.copy(), name=name)


def table_to_bintablehdu(table, extname=None):
    """Convert an astropy Table object to a BinTableHDU before writing to disk.

    Parameters
    ----------
    table: astropy.table.Table instance
        the table to be converted to a BinTableHDU

    extname: str
        name to go in the EXTNAME field of the FITS header

    Returns
    -------
    BinTableHDU
    """
    # remove header to avoid warning from table_to_hdu
    table_header = table.meta.pop("header", None)

    # table_to_hdu sets units only if the unit conforms to the FITS standard,
    # otherwise it issues a warning, which we catch here.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        hdu = fits.table_to_hdu(table)

    # And now we try to set the units that do not conform to the standard,
    # using unit.to_string() without the format='fits' argument.
    for col in table.itercols():
        if col.unit and not hdu.columns[col.name].unit:
            hdu.columns[col.name].unit = col.unit.to_string()

    if table_header is not None:
        # Update with cards from table.meta, but skip structural FITS
        # keywords since those have been set by table_to_hdu
        exclude = (
            "SIMPLE",
            "XTENSION",
            "BITPIX",
            "NAXIS",
            "EXTEND",
            "PCOUNT",
            "GCOUNT",
            "TFIELDS",
            "TFORM",
            "TSCAL",
            "TZERO",
            "TNULL",
            "TTYPE",
            "TUNIT",
            "TDISP",
            "TDIM",
            "THEAP",
            "TBCOL",
        )
        hdr = fits.Header(
            [
                card
                for card in table_header.cards
                if not card.keyword.startswith(exclude)
            ]
        )
        update_header(hdu.header, hdr)
        # reset table's header
        table.meta["header"] = table_header
    if extname:
        hdu.header["EXTNAME"] = (extname, "added by AstroData")
    return hdu


def header_for_table(table):
    """Return a FITS header for a table."""
    table_header = table.meta.pop("header", None)
    fits_header = fits.table_to_hdu(table).header

    if table_header:
        table.meta["header"] = table_header  # restore original meta
        fits_header = update_header(table_header, fits_header)

    return fits_header


def add_header_to_table(table):
    """Add a FITS header to a table."""
    header = header_for_table(table)
    table.meta["header"] = header
    return header


def _process_table(table, name=None, header=None):
    """Convert a BinTableHDU or TableHDU to an astropy Table object.

    Arguments
    ---------
    table : |BinTableHDU| or |TableHDU| or |Table|
        The table to convert. If it's already an |Table|, it will be returned
        as is.

    name : str
        The name to assign to the table.

    header : `astropy.io.fits.Header`
        The header to assign to the table.
    """
    if isinstance(table, (BinTableHDU, TableHDU)):
        obj = Table(table.data, meta={"header": header or table.header})
        for i, col in enumerate(obj.columns, start=1):
            try:
                obj[col].unit = u.Unit(obj.meta["header"][f"TUNIT{i}"])
            except (KeyError, TypeError, ValueError):
                pass
    elif isinstance(table, Table):
        obj = Table(table)
        if header is not None:
            obj.meta["header"] = deepcopy(header)
        elif "header" not in obj.meta:
            obj.meta["header"] = header_for_table(obj)
    else:
        raise ValueError(f"{table.__class__} is not a recognized table type")

    if name is not None:
        obj.meta["header"]["EXTNAME"] = name

    return obj


def card_filter(cards, include=None, exclude=None):
    """Filter a list of cards, lazily returning only those that match the
    criteria.

    Parameters
    ----------
    cards : iterable
        The cards to filter.

    include : iterable of str
        Only cards with these keywords will be returned.

    exclude : iterable of str
        Cards with these keywords will be skipped.

    Yields
    ------
    card : tuple
        A card that matches the criteria.
    """
    for card in cards:
        if include is not None and card[0] not in include:
            continue

        if exclude is not None and card[0] in exclude:
            continue

        yield card


def update_header(headera, headerb):
    """Update headera with the cards from headerb, but only if they are
    different.

    Parameters
    ----------
    headera : `astropy.io.fits.Header`
        The header to update.

    headerb : `astropy.io.fits.Header`
        The header to update from.
    """
    cardsa = tuple(tuple(cr) for cr in headera.cards)
    cardsb = tuple(tuple(cr) for cr in headerb.cards)

    if cardsa == cardsb:
        return headera

    # Ok, headerb differs somehow. Let's try to bring the changes to headera
    # Updated keywords that should be unique
    difference = set(cardsb) - set(cardsa)
    headera.update(card_filter(difference, exclude={"HISTORY", "COMMENT", ""}))

    # Check the HISTORY and COMMENT cards, just in case
    for key in ("HISTORY", "COMMENT"):
        fltcardsa = card_filter(cardsa, include={key})
        fltcardsb = card_filter(cardsb, include={key})
        # assume we start with two headers that are mostly the same and
        # that will have added comments/history at the end (in headerb)
        for ca, cb in zip_longest(fltcardsa, fltcardsb):
            if ca is None:
                headera.update((cb,))

    return headera


def fits_ext_comp_key(ext):
    """Returns a pair (int, str) that will be used to sort extensions."""
    if isinstance(ext, PrimaryHDU):
        # This will guarantee that the primary HDU goes first
        ret = (-1, "")
    else:
        # When two extensions share version number, we'll use their names
        # to sort them out. Choose a suitable key so that:
        #
        #  - SCI extensions come first
        #  - unnamed extensions come last
        #
        # We'll resort to add 'z' in front of the usual name to force
        # SCI to be the "smallest"
        name = ext.name
        if name == "":
            name = "zzzz"
        elif name != DEFAULT_EXTENSION:
            name = "z" + name

        ver = ext.header.get("EXTVER")
        if ver in (-1, None):
            # In practice, this number should be larger than any EXTVER found
            # in real life HDUs, pushing unnumbered HDUs to the end.
            ver = 2**32 - 1

        # For the general case, just return version and name, to let them
        # be sorted naturally
        ret = (ver, name)

    return ret


class FitsLazyLoadable:
    """Class to delay loading of data from a FITS file."""

    def __init__(self, obj):
        """Initializes the object.

        Parameters
        ----------
        obj : `astropy.io.fits.ImageHDU` or `astropy.io.fits.BinTableHDU`
            The HDU to delay loading from.
        """
        self._obj = obj
        self.lazy = True

    def _create_result(self, shape):
        """Create an empty array to hold the data."""
        return np.empty(shape, dtype=self.dtype)

    def _scale(self, data):
        """Scale the data, if necessary."""
        # pylint: disable=protected-access
        bscale = self._obj._orig_bscale
        bzero = self._obj._orig_bzero

        # If bscale is None, then the data is already scaled
        if bscale is None:
            return data

        if bscale == 1 and bzero == 0:
            return data

        return (bscale * data + bzero).astype(self.dtype)

    def __getitem__(self, arr_slice):
        return self._scale(self._obj.section[arr_slice])

    @property
    def header(self):
        """The header of the HDU."""
        return self._obj.header

    @property
    def data(self):
        """The data of the HDU."""
        res = self._create_result(self.shape)
        res[:] = self._scale(self._obj.data)
        return res

    @property
    def shape(self):
        """The shape of the data."""
        return self._obj.shape

    @property
    def dtype(self):
        """Need to to some overriding of astropy.io.fits since it doesn't
        know about BITPIX=8
        """
        # pylint: disable=protected-access
        bitpix = self._obj._orig_bitpix

        if self._obj._orig_bscale == 1 and self._obj._orig_bzero == 0:
            dtype = fits.BITPIX2DTYPE[bitpix]

        else:
            # this method from astropy will return the dtype if the data
            # needs to be converted to unsigned int or scaled to float
            dtype = self._obj._dtype_for_bitpix()

        if dtype is None:
            if bitpix < 0:
                dtype = np.dtype(f"float{abs(bitpix)}")

        if (
            self._obj.header["EXTNAME"] == "DQ"
            or self._obj._uint
            and self._obj._orig_bscale == 1
            and bitpix == 8
        ):
            dtype = np.uint16

        return dtype


def _prepare_hdulist(hdulist, default_extension="SCI", extname_parser=None):
    """Prepare an HDUList for reading.

    Parameters
    ----------
    hdulist : `astropy.io.fits.HDUList`
        The HDUList to prepare.

    default_extension : str
        The name of the default extension.

    extname_parser : callable
        A function to parse the EXTNAME of an HDU.

    Returns
    -------
    hdulist : `astropy.io.fits.HDUList`
        The prepared HDUList.
    """
    new_list = []
    highest_ver = 0
    recognized = set()

    if len(hdulist) > 1 or (len(hdulist) == 1 and hdulist[0].data is None):
        # MEF file
        # First get HDUs for which EXTVER is defined
        for hdu in hdulist:
            if extname_parser:
                extname_parser(hdu)
            ver = hdu.header.get("EXTVER")
            if ver not in (-1, None) and hdu.name:
                highest_ver = max(highest_ver, ver)
            elif not isinstance(hdu, PrimaryHDU):
                continue

            new_list.append(hdu)
            recognized.add(hdu)

        # Then HDUs that miss EXTVER
        for hdu in hdulist:
            if hdu in recognized:
                continue

            if isinstance(hdu, ImageHDU):
                highest_ver += 1
                if "EXTNAME" not in hdu.header:
                    hdu.header["EXTNAME"] = (
                        default_extension,
                        "Added by AstroData",
                    )

                if hdu.header.get("EXTVER") in (-1, None):
                    hdu.header["EXTVER"] = (highest_ver, "Added by AstroData")

            new_list.append(hdu)
            recognized.add(hdu)

    else:
        # Uh-oh, a single image FITS file
        new_list.append(PrimaryHDU(header=hdulist[0].header))
        image = ImageHDU(header=hdulist[0].header, data=hdulist[0].data)
        # Fudge due to apparent issues with assigning ImageHDU from data
        # pylint: disable=protected-access
        image._orig_bscale = hdulist[0]._orig_bscale
        image._orig_bzero = hdulist[0]._orig_bzero

        for keyw in ("SIMPLE", "EXTEND"):
            if keyw in image.header:
                del image.header[keyw]

        image.header["EXTNAME"] = (default_extension, "Added by AstroData")
        image.header["EXTVER"] = (1, "Added by AstroData")
        new_list.append(image)

    return HDUList(sorted(new_list, key=fits_ext_comp_key))


def read_fits(cls, source, extname_parser=None):
    """Takes either a string (with the path to a file) or an HDUList as input,
    and tries to return a populated AstroData (or descendant) instance.

    It will raise exceptions if the file is not found, or if there is no match
    for the HDUList, among the registered AstroData classes.

    Parameters
    ----------
    cls : class
        The class to instantiate.

    source : str or `astropy.io.fits.HDUList`
        The path to the file, or an HDUList.

    extname_parser : callable
        A function to parse the EXTNAME of an HDU.

    Returns
    -------
    ad : `astrodata.AstroData` or descendant
        The populated AstroData object. This is of the type specified by cls.
    """

    ad = cls()

    if isinstance(source, (str, os.PathLike)):
        hdulist = fits.open(
            source, memmap=True, do_not_scale_image_data=True, mode="readonly"
        )

        ad.path = source

    else:
        hdulist = source

        try:
            ad.path = source[0].header.get("ORIGNAME")

        except AttributeError as err:
            logging.info("Attribute error in read_fits: %s", err)
            ad.path = None

    # This is a hack to get around the fact that we don't have a proper way to
    # pass the original filename to the object. This is needed for the writer
    # to be able to write the ORIGNAME keyword.
    # pylint: disable=protected-access
    _file = hdulist._file

    hdulist = _prepare_hdulist(
        hdulist,
        default_extension=DEFAULT_EXTENSION,
        extname_parser=extname_parser,
    )

    if _file is not None:
        hdulist._file = _file

    # Initialize the object containers to a bare minimum
    # pylint: disable=no-member
    if "ORIGNAME" not in hdulist[0].header and ad.orig_filename is not None:
        hdulist[0].header.set(
            "ORIGNAME",
            ad.orig_filename,
            "Original filename prior to processing",
        )

    ad.phu = hdulist[0].header

    # This is hashable --- we can use it to check if we've seen this object
    # before.
    # pylint: disable=unhashable-member
    seen = {hdulist[0]}

    skip_names = {DEFAULT_EXTENSION, "REFCAT", "MDF"}

    def associated_extensions(ver):
        for hdu in hdulist:
            if hdu.header.get("EXTVER") == ver and hdu.name not in skip_names:
                yield hdu

    # Only SCI HDUs
    sci_units = [hdu for hdu in hdulist[1:] if hdu.name == DEFAULT_EXTENSION]

    seen_vers = []

    for hdu in sci_units:
        seen.add(hdu)
        ver = hdu.header.get("EXTVER", -1)

        if ver > -1 and seen_vers.count(ver) == 1:
            LOGGER.warning("Multiple SCI extension with EXTVER %s", ver)

        seen_vers.append(ver)
        parts = {
            "data": hdu,
            "uncertainty": None,
            "mask": None,
            "wcs": None,
            "other": [],
        }

        # For each SCI HDU find if it has an associated variance, mask, wcs
        for extra_unit in associated_extensions(ver):
            seen.add(extra_unit)
            name = extra_unit.name
            if name == "DQ":
                parts["mask"] = extra_unit
            elif name == "VAR":
                parts["uncertainty"] = extra_unit
            elif name == "WCS":
                parts["wcs"] = extra_unit
            else:
                parts["other"].append(extra_unit)

        header = parts["data"].header
        lazy = hdulist._file is not None and hdulist._file.memmap

        for part_name in ("data", "mask", "uncertainty"):
            if parts[part_name] is not None:
                if lazy:
                    # Use FitsLazyLoadable to delay loading of the data
                    parts[part_name] = FitsLazyLoadable(parts[part_name])
                else:
                    #  We open the file with do_not_scale_data=True, so
                    #  the data array does not have the correct data values.
                    #  AstroData handles scaling internally, and we can ensure
                    #  it does that by making the data a FitsLazyLoadable; the
                    #  side-effect of this is that the is_lazy() function will
                    #  return True, but this has minimal knock-on effects.
                    #  Hopefully astropy will handle this better in future.
                    if hdulist._file is not None:  # probably compressed
                        parts[part_name] = FitsLazyLoadable(parts[part_name])

                    else:  # for astrodata.create() files
                        parts[part_name] = parts[part_name].data

        # handle the variance if not lazy
        if parts["uncertainty"] is not None and not isinstance(
            parts["uncertainty"], FitsLazyLoadable
        ):
            parts["uncertainty"] = ADVarianceUncertainty(parts["uncertainty"])

        # Create the NDData object
        nd = NDAstroData(
            data=parts["data"],
            uncertainty=parts["uncertainty"],
            mask=parts["mask"],
            meta={"header": header},
        )

        ad.append(nd, name=DEFAULT_EXTENSION)

        # This is used in the writer to keep track of the extensions that
        # were read from the current object.
        nd.meta["parent_ad"] = id(ad)

        for other in parts["other"]:
            if not other.name:
                warnings.warn(f"Skip HDU {other} because it has no EXTNAME")
            else:
                setattr(ad[-1], other.name, other)

        if parts["wcs"] is not None:
            # Load the gWCS object from the ASDF extension
            nd.wcs = asdftablehdu_to_wcs(parts["wcs"])
        if nd.wcs is None:
            # Fallback to the data header
            nd.wcs = fitswcs_to_gwcs(nd)
            if nd.wcs is None:
                # In case WCS info is in the PHU
                nd.wcs = fitswcs_to_gwcs(hdulist[0].header)

    for other in hdulist:
        if other in seen:
            continue

        name = other.header.get("EXTNAME")

        try:
            ad.append(other, name=name)

        except ValueError as e:
            warnings.warn(f"Discarding {name} :\n {e}")

    return ad


def ad_to_hdulist(ad):
    """Creates an HDUList from an AstroData object."""
    hdul = HDUList()
    hdul.append(PrimaryHDU(header=ad.phu, data=DELAYED))

    # Find the maximum EXTVER for extensions that belonged with this
    # object if it was read from a FITS file
    # pylint: disable=protected-access
    ad_nddata = ad.nddata

    if isinstance(ad_nddata, NDAstroData):
        ad_nddata = [ad_nddata]

    maxver = max(
        (
            nd.meta["header"].get("EXTVER", 0)
            for nd in ad_nddata
            if nd.meta.get("parent_ad") == id(ad)
        ),
        default=0,
    )

    for ext in ad_nddata:
        header = ext.meta["header"].copy()

        if not isinstance(header, fits.Header):
            header = fits.Header(header)

        if ext.meta.get("parent_ad") == id(ad):
            # If the extension belonged with this object, use its
            # original EXTVER
            ver = header["EXTVER"]
        else:
            # Otherwise renumber the extension
            ver = header["EXTVER"] = maxver + 1
            maxver += 1

        wcs = ext.wcs

        if isinstance(wcs, gWCS):
            # We don't have access to the AD tags so see if it's an image
            # Catch ValueError as any sort of failure
            try:
                wcs_dict = gwcs_to_fits(ext, ad.phu)

            except (ValueError, NotImplementedError) as e:
                LOGGER.warning(e)

            else:
                # Must delete keywords if image WCS has been downscaled
                # from a higher number of dimensions
                for i in range(1, 5):
                    for kw in (
                        f"CDELT{i}",
                        f"CRVAL{i}",
                        f"CUNIT{i}",
                        f"CTYPE{i}",
                        f"NAXIS{i}",
                    ):
                        if kw in header:
                            del header[kw]

                    for j in range(1, 5):
                        for kw in (f"CD{i}_{j}", f"PC{i}_{j}", f"CRPIX{j}"):
                            if kw in header:
                                del header[kw]

                # Delete this if it's left over from a previous save
                if "FITS-WCS" in header:
                    del header["FITS-WCS"]

                try:
                    extensions = wcs_dict.pop("extensions")

                except KeyError:
                    pass

                else:
                    for k, v in extensions.items():
                        ext.meta["other"][k] = v

                header.update(wcs_dict)

                # Use "in" here as the dict entry may be (value, comment)
                if "APPROXIMATE" not in wcs_dict.get("FITS-WCS", ""):
                    wcs = None  # There's no need to create a WCS extension

        hdul.append(new_imagehdu(ext.data, header, "SCI"))

        if ext.uncertainty is not None:
            hdul.append(new_imagehdu(ext.uncertainty.array, header, "VAR"))

        if ext.mask is not None:
            hdul.append(new_imagehdu(ext.mask, header, "DQ"))

        if isinstance(wcs, gWCS):
            hdul.append(wcs_to_asdftablehdu(ext.wcs, extver=ver))

        for name, other in ext.meta.get("other", {}).items():
            if isinstance(other, Table):
                hdu = table_to_bintablehdu(other, extname=name)

            elif isinstance(other, np.ndarray):
                hdu = new_imagehdu(other, header, name=name)

            elif isinstance(other, NDAstroData):
                hdu = new_imagehdu(other.data, ext.meta["header"])

            else:
                raise ValueError(
                    "I don't know how to write back an object "
                    f"of type {type(other)}"
                )

            hdu.ver = ver
            hdul.append(hdu)

    if ad._tables is not None:
        for name, table in sorted(ad._tables.items()):
            hdul.append(table_to_bintablehdu(table, extname=name))

    # Additional FITS compatibility, add to PHU
    # pylint: disable=no-member
    hdul[0].header["NEXTEND"] = len(hdul) - 1

    return hdul


def write_fits(ad, filename, overwrite=False):
    """Writes the AstroData object to a FITS file."""
    hdul = ad_to_hdulist(ad)
    hdul.writeto(filename, overwrite=overwrite)


@deprecated(
    "Renamed to 'windowed_operation', this is just an alias for now, "
    "and will be removed in a future version."
)
def windowedOp(*args, **kwargs):  # pylint: disable=invalid-name
    """Deprecated alias for windowed_operation."""
    return windowed_operation(*args, **kwargs)


def _generate_boxes(shape, kernel):
    """Break the input into chunks."""
    if len(shape) != len(kernel):
        raise AssertionError(
            f"Incompatible shape ({shape}) and kernel ({kernel})"
        )

    ticks = [
        [(x, x + step) for x in range(0, axis, step)]
        for axis, step in zip(shape, kernel)
    ]

    return list(cart_product(*ticks))


def _get_shape(sequence):
    """Get the shape of the input."""
    if len({x.shape for x in sequence}) > 1:
        shapes = tuple(x.shape for x in sequence)
        raise ValueError(
            f"Can't calculate final shape: sequence elements "
            f"mismatch on shape, and none was provided."
            f" (shapes: {shapes}, found "
            f" {len(set(shapes))} unique shapes: {tuple(set(shapes))}"
        )

    return sequence[0].shape


def _apply_func(func, sequence, boxes, result, **kwargs):
    """
    Apply a given function to a sequence of elements within specified boxes and store the result in the result object.

    Parameters
    ----------
    func : function
        The function to apply to the elements.
    sequence : list
        The sequence of elements to apply the function to.
    boxes : list
        The list of boxes specifying the sections of the elements to apply the function to.
    result : object
        The object to store the result in.

    Returns
    -------
    None

    Note
    ----
    This function applies the function to the elements in the sequence within
    the specified boxes and stores the result in the result object. There is no
    data returned by this function.
    """
    for coords in boxes:
        section = tuple(slice(start, end) for (start, end) in coords)
        out = func([element.window[section] for element in sequence], **kwargs)
        result.set_section(section, out)

        # propagate additional attributes
        if out.meta.get("other"):
            for k, v in out.meta["other"].items():
                if len(boxes) > 1:
                    result.meta["other"][k, coords] = v
                else:
                    result.meta["other"][k] = v

        gc.collect()


def windowed_operation(
    func,
    sequence,
    kernel,
    shape=None,
    dtype=None,
    with_uncertainty=False,
    with_mask=False,
    **kwargs,
):
    """Apply function on a NDData obbjects, splitting the data in chunks to
    limit memory usage.

    Parameters
    ----------
    func : callable
        The function to apply.

    sequence : list of NDData
        List of NDData objects.

    kernel : tuple of int
        Shape of the blocks.

    shape : tuple of int
        Shape of inputs. Defaults to ``sequence[0].shape``.

    dtype : str or dtype
        Type of the output array. Defaults to ``sequence[0].dtype``.

    with_uncertainty : bool
        Compute uncertainty?

    with_mask : bool
        Compute mask?

    **kwargs
        Additional args are passed to ``func``.
    """
    if shape is None:
        shape = _get_shape(sequence)

    if dtype is None:
        dtype = sequence[0].window[:1, :1].data.dtype

    result = NDAstroData(
        np.empty(shape, dtype=dtype),
        variance=np.zeros(shape, dtype=dtype) if with_uncertainty else None,
        mask=np.empty(shape, dtype=np.uint16) if with_mask else None,
        meta=sequence[0].meta,
        wcs=sequence[0].wcs,
    )

    # Delete other extensions because we don't know what to do with them
    result.meta["other"] = OrderedDict()

    # The Astropy logger's "INFO" messages aren't warnings, so have to fudge
    # pylint: disable=no-member
    log_level = astropy.logger.conf.log_level
    astropy.log.setLevel(astropy.logger.WARNING)

    boxes = _generate_boxes(shape, kernel)

    try:
        _apply_func(func, sequence, boxes, result, **kwargs)

    finally:
        astropy.log.setLevel(log_level)  # and reset

    # Now if the input arrays where splitted in chunks, we need to gather
    # the data arrays for the additional attributes.
    other = result.meta["other"]
    if other:
        if len(boxes) > 1:
            for (name, coords), obj in list(other.items()):
                if not isinstance(obj, NDData):
                    raise ValueError("only NDData objects are handled here")

                if name not in other:
                    other[name] = NDAstroData(
                        np.empty(shape, dtype=obj.data.dtype)
                    )

                section = tuple(slice(start, end) for (start, end) in coords)
                other[name].set_section(section, obj)

                del other[name, coords]

        for name in other:
            # To set the name of our object we need to save it as an ndarray,
            # otherwise for a NDData one AstroData would use the name of the
            # AstroData object.
            other[name] = other[name].data

    return result


# ---------------------------------------------------------------------------
# gWCS <-> FITS WCS helper functions go here
# ---------------------------------------------------------------------------
# Could parametrize some naming conventions in the following two functions if
# done elsewhere for hard-coded names like 'SCI' in future, but they only have
# to be self-consistent with one another anyway.


def wcs_to_asdftablehdu(wcs, extver=None):
    """Serialize a gWCS object as a FITS TableHDU (ASCII) extension.

    The ASCII table is actually a mini ASDF file. The constituent AstroPy
    models must have associated ASDF "tags" that specify how to serialize them.

    In the event that serialization as pure ASCII fails (this should not
    happen), a binary table representation will be used as a fallback.

    Returns None (issuing a warning) if the WCS object cannot be serialized,
    so the rest of the file can still be written.

    Parameters
    ----------
    wcs : gWCS
        The gWCS object to serialize.

    extver : int
        The EXTVER to assign to the extension.

    Returns
    -------
    hdu : TableHDU or BinTableHDU
        The FITS table extension containing the serialized WCS object.
    """
    # Create a small ASDF file in memory containing the WCS object
    # representation because there's no public API for generating only the
    # relevant YAML subsection and an ASDF file handles the "tags" properly.
    try:
        af = asdf.AsdfFile({"wcs": wcs})
    except jsonschema.exceptions.ValidationError as err:
        # (The original traceback also gets printed here)
        raise TypeError(
            f"Cannot serialize model(s) for 'WCS' extension " f"{extver or ''}"
        ) from err

    # ASDF can only dump YAML to a binary file object, so do that and read
    # the contents back from it for storage in a FITS extension:
    with BytesIO() as fd:
        with af:
            # Generate the YAML, dumping any binary arrays as text:
            af.write_to(fd, all_array_storage="inline")
        fd.seek(0)
        wcsbuf = fd.read()

    # Convert the bytes to readable lines of text for storage (falling back to
    # saving as binary in the unexpected event that this is not possible):
    try:
        wcsbuf = wcsbuf.decode("ascii").splitlines()

    except UnicodeDecodeError as err:
        # This should not happen, but if the ASDF contains binary data in
        # spite of the 'inline' option above, we have to dump the bytes to
        # a non-human-readable binary table rather than an ASCII one:
        LOGGER.warning(
            "Could not convert WCS %s ASDF to ASCII; saving table "
            "as binary (error was %s)",
            extver or "",
            err,
        )

        hduclass = BinTableHDU
        fmt = "B"
        wcsbuf = np.frombuffer(wcsbuf, dtype=np.uint8)

    else:
        hduclass = TableHDU
        fmt = f"A{max(len(line) for line in wcsbuf)}"

    # Construct the FITS table extension:
    col = Column(
        name="gWCS", format=fmt, array=wcsbuf, ascii=hduclass is TableHDU
    )

    return hduclass.from_columns([col], name="WCS", ver=extver)


def asdftablehdu_to_wcs(hdu):
    """Recreate a gWCS object from its serialization in a FITS table extension.

    Returns None (issuing a warning) if the extension cannot be parsed, so
    the rest of the file can still be read.
    """
    ver = hdu.header.get("EXTVER", -1)

    if isinstance(hdu, (TableHDU, BinTableHDU)):
        try:
            colarr = hdu.data["gWCS"]

        except KeyError as err:
            LOGGER.warning(
                "Ignoring 'WCS' extension %s with no 'gWCS' table "
                "column (error was %s)",
                ver,
                err,
            )

            return None

        # If this table column contains text strings as expected, join the rows
        # as separate lines of a string buffer and encode the resulting YAML as
        # bytes that ASDF can parse. If AstroData has produced another format,
        # it will be a binary dump due to the unexpected presence of non-ASCII
        # data, in which case we just extract unmodified bytes from the table.
        if colarr.dtype.kind in ("U", "S"):
            sep = os.linesep
            # Just in case io.fits ever produces 'S' on Py 3 (not the default):
            # join lines as str & avoid a TypeError with unicode linesep; could
            # also use astype('U') but it assumes an encoding implicitly.
            if colarr.dtype.kind == "S" and not isinstance(sep, bytes):
                colarr = np.char.decode(
                    np.char.rstrip(colarr), encoding="ascii"
                )
            wcsbuf = sep.join(colarr).encode("ascii")
        else:
            wcsbuf = colarr.tobytes()

        # Convert the stored text to a Bytes file object that ASDF can open:
        with BytesIO(wcsbuf) as fd:
            # Try to extract a 'wcs' entry from the YAML:
            try:
                af = asdf.open(fd)

            except IOError:
                LOGGER.warning(
                    "Ignoring 'WCS' extension %s: failed to parse "
                    "ASDF.\nError was as follows:\n%s",
                    ver,
                    traceback.format_exc(),
                )

                return None

            with af:
                try:
                    wcs = af.tree["wcs"]

                except KeyError as err:
                    LOGGER.warning(
                        "Ignoring 'WCS' extension %s: missing "
                        "'wcs' dict entry. Error was %s",
                        ver,
                        err,
                    )

                    return None

    else:
        LOGGER.warning("Ignoring non-FITS-table 'WCS' extension %s", ver)

        return None

    return wcs

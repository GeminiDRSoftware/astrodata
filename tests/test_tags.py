import os
import numpy as np
import pytest
from astropy.io import fits
from astropy.table import Table

import astrodata
from astrodata import (
    astro_data_tag,
    astro_data_descriptor,
    TagSet,
    AstroData,
    returns_list,
)

SHAPE = (4, 5)


class AstroDataMyInstrument(AstroData):
    __keyword_dict = dict(array_name="AMPNAME", array_section="CCDSECT")

    @staticmethod
    def _matches_data(source):
        return source[0].header.get("INSTRUME", "").upper() == "MYINSTRUMENT"

    @astro_data_tag
    def _tag_instrument(self):
        return TagSet(["MYINSTRUMENT"])

    @astro_data_tag
    def _tag_image(self):
        if self.phu.get("GRATING") == "MIRROR":
            return TagSet(["IMAGE"])

    @astro_data_tag
    def _tag_dark(self):
        if self.phu.get("OBSTYPE") == "DARK":
            return TagSet(["DARK"], blocks=["IMAGE", "SPECT"])

    @astro_data_tag
    def _tag_raise(self):
        raise KeyError  # I guess if some keyword is missing...

    @returns_list
    @astro_data_descriptor
    def dispersion_axis(self):
        return 1

    @returns_list
    @astro_data_descriptor
    def gain(self):
        return [1, 1]

    @returns_list
    @astro_data_descriptor
    def badguy(self):
        return [1, 2, 3]

    @astro_data_descriptor
    def array_name(self):
        return self.phu.get(self._keyword_for("array_name"))

    @astro_data_descriptor
    def detector_section(self):
        return self.phu.get(self._keyword_for("array_section"))

    @astro_data_descriptor
    def amp_read_area(self):
        ampname = self.array_name()
        detector_section = self.detector_section()
        return "'{}':{}".format(ampname, detector_section)


def setup_function():
    """Add the new class to the factory."""
    from astrodata import factory

    factory.add_class(AstroDataMyInstrument)


@pytest.fixture
def testfile(tmp_path):
    hdr = fits.Header(
        {
            "INSTRUME": "MYINSTRUMENT",
            "GRATING": "MIRROR",
            "OBSTYPE": "DARK",
            "AMPNAME": "FOO",
            "CCDSECT": "1:1024",
        }
    )
    phu = fits.PrimaryHDU(header=hdr)
    hdu = fits.ImageHDU(data=np.ones(SHAPE))
    hdu2 = fits.ImageHDU(data=np.ones(SHAPE) + 1)
    ad = astrodata.create(phu, [hdu, hdu2])
    tbl = Table([np.zeros(10), np.ones(10)], names=["col1", "col2"])
    ad.MYCAT = tbl
    # Generate unique filename for each test
    filename = os.path.join(tmp_path, "fakebias.fits")
    ad.write(filename)
    yield filename


def test_tags(testfile):
    ad = astrodata.from_file(testfile)
    assert ad.descriptors == (
        "amp_read_area",
        "array_name",
        "badguy",
        "detector_section",
        "dispersion_axis",
        "gain",
        "instrument",
        "object",
        "telescope",
    )
    assert ad.tags == {"DARK", "MYINSTRUMENT"}
    assert ad.amp_read_area() == "'FOO':1:1024"


def test_keyword_for(testfile):
    ad = astrodata.from_file(testfile)
    assert ad._keyword_for("array_name") == "AMPNAME"
    with pytest.raises(AttributeError, match="No match for 'foobar'"):
        ad._keyword_for("foobar")


def test_returns_list(testfile):
    ad = astrodata.from_file(testfile)
    assert ad.dispersion_axis() == [1, 1]
    assert ad[0].dispersion_axis() == 1

    assert ad.gain() == [1, 1]
    assert ad[0].gain() == 1

    with pytest.raises(IndexError):
        ad.badguy()


def test_info(testfile, capsys):
    ad = astrodata.from_file(testfile)
    ad.info()
    captured = capsys.readouterr()
    out = captured.out.splitlines()
    assert out[0].endswith("fakebias.fits")
    assert out[1:] == [
        "Tags: DARK MYINSTRUMENT",
        "",
        "Pixels Extensions",
        "Index  Content                  Type              Dimensions     Format",
        "[ 0]   science                  NDAstroData       (4, 5)         float64",
        "[ 1]   science                  NDAstroData       (4, 5)         float64",
        "",
        "Other Extensions",
        "               Type        Dimensions",
        ".MYCAT         Table       (10, 2)",
    ]

    ad[1].info()
    captured = capsys.readouterr()
    out = captured.out.splitlines()
    assert out[0].endswith("fakebias.fits")
    assert out[1:] == [
        "Tags: DARK MYINSTRUMENT",
        "",
        "Pixels Extensions",
        "Index  Content                  Type              Dimensions     Format",
        "[ 0]   science                  NDAstroData       (4, 5)         float64",
        "",
        "Other Extensions",
        "               Type        Dimensions",
        ".MYCAT         Table       (10, 2)",
    ]

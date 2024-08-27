[DRAGONS link]: https://github.com/GeminiDRSoftware/DRAGONS
[astrodata docs]: https://geminidrsoftware.github.io/astrodata/
[astrodata repo]: https://github.com/GeminiDRSoftware/astrodata/
[astropy link]: https://astropy.org
[pypi link]: https://pypi.org/project/astrodata
[citation link]: https://github.com/GeminiDRSoftware/astrodata/blob/main/CITATION.md
[DRAGONS citation]: https://zenodo.org/records/10841622

[coverage badge]: https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/teald/d2f3af2a279efc1f6e90d457a3c50e47/raw/covbadge.json
[docs build badge]: https://github.com/GeminiDRSoftware/astrodata/actions/workflows/documentation.yml/badge.svg
[pypi packaging badge]: https://github.com/GeminiDRSoftware/astrodata/actions/workflows/publish_pypi.yml/badge.svg
[pypi package version badge]: https://badge.fury.io/py/astrodata.svg
[source test status badge]: https://github.com/GeminiDRSoftware/astrodata/actions/workflows/source_tests.yml/badge.svg
[build test status badge]: https://github.com/GeminiDRSoftware/astrodata/actions/workflows/build_tests.yml/badge.svg

`astrodata`
=============

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/static/logo.svg">
  <img
  alt="A logo of a stylized blue dragon inside a similarly blue shell. A yellow star lies at the center, together with the dragon shape forming a stylized letter A."
  src="docs/static/logo_dark.svg"
  align="left"
  height=200
  style="padding-right: 10; padding-bottom: 10; border: none;"
  >
</picture>

[![Project Status: Active – The project has reached a stable, usable state and is being actively developed.](https://www.repostatus.org/badges/latest/active.svg)](https://www.repostatus.org/#active)
![Supported python versions -- 3.10, 3.11, and 3.12](https://img.shields.io/badge/3.10|3.11|3.12-%234b8bbe?logo=Python&logoColor=%234b8bbe&label=For%20Python%3A)
[![PyPI version badge][pypi package version badge]](https://badge.fury.io/py/astrodata)

### Tests
![A badge displaying the testing coverage percentage of this repository.][coverage badge]
![Source test status badge][source test status badge]
![Build/Release test status badge][build test status badge]

### Building & Publishing
![Documentation build status badge][docs build badge]
![pypi packaging status badge][pypi packaging badge]

<!-- Clearing the logo for the next header -->
<br clear="left">

Making astronomical data consistent and approachable
--------------------------------------------------------------------

`astrodata` is a package for managing astronomical data through a uniform
interface. It is designed to be used with the
[Astropy package][astropy link]. `astrodata` was created
for use as part of the [`DRAGONS`][DRAGONS link] data reduction pipeline, but it is now
implemented to be useful for any astronomical data reduction or analysis
project.

Unlike managing files using the ``astropy.io.fits`` package alone, ``astrodata``
is designed to be extendible to any data format, and to parse, respond to, and
store metadata in a consistent, intentional way. This makes it especially
useful for managing data from multiple instruments, telescopes, and data
generation utilities.

**Note:** If you are trying to reduce Gemini data, please use [`DRAGONS`][DRAGONS link].
Interaction with this package directly is primarily suited for developers, and
does not come with any tools for data reduction on any specific instrument or
data.

Installation
------------

`astrodata` is available on the [Python Package Index][pypi link] and
can be installed using `pip`:

```
python -m pip install astrodata
```

Documentation
-------------

Documentation for ``astrodata`` is available on our [GitHub pages site][astrodata docs]. This documentation includes a
user and programmer's guide, as well as a full API reference.


Usage
-----

The most basic usage of ``astrodata`` is to extend the ``astrodata.AstroData``
class, which includes some basic FITS file handling methods by default:

```python
from astrodata import AstroData, astro_data_descriptor, factory, from_file


class MyData(AstroData):
    @astro_data_descriptor
    def color(self):
        # The color filter used for our image is stored in a few different
        # ways, let's unify them.
        blue_labels = {"blue", "bl", "b"}
        green_labels = {"green", "gr", "g"}
        red_labels = {"red", "re", "r"}

        header_value = self.phu.get("COLOR", None).casefold()

        if header_value in blue_labels:
            return "BLUE"

        if header_value in green_labels:
            return "GREEN"

        if header_value in red_labels:
            return "RED"

        if header_value is None:
            raise ValueError("No color found")

        # Unrecognized color
        raise ValueError(f"Did not recognize COLOR value: {header_value}")


# Now, define our instruments with nuanced, individual data formats
class MyInstrument1(MyData):
    # These use a special method to resolve the metadata and apply the correct
    # class.
    @staticmethod
    def _matches_data(source):
        return source[0].header.get("INSTRUME", "").upper() == "MYINSTRUMENT1"


class MyInstrument2(MyData):
    @staticmethod
    def _matches_data(source):
        return source[0].header.get("INSTRUME", "").upper() == "MYINSTRUMENT2"


class MyInstrument3(MyData):
    @staticmethod
    def _matches_data(source):
        return source[0].header.get("INSTRUME", "").upper() == "MYINSTRUMENT3"


for cls in [MyInstrument1, MyInstrument2, MyInstrument3]:
    factory.add_class(cls)

# my_file.fits has some color data depending on the instrument it comes from,
# but now we can access it and handle a single value.
data = from_file("README_example.fits")

# the astrodata factory has already resolved the correct class for us.
print(f"File used to create class: {data.__class__.__name__}")
if data.color() == "BLUE":
    print("I used the blue filter!")

else:
    print("I used a red or green filter!")

# Get all the info about the astrodata object.
data.info()

```

This will print out the filter used as extracted from the header of the FITS
file. `data.info()` offers a more complete look at the file's data including
the filename and path of the file (as it does for `astropy.io.fits` objects).

`astrodata` is designed to be extensible, so you can add your own methods to
analyze and process data based on your specific needs and use cases.

`astrodata` also has a number of built in features, including:

+ Operator support for arithmetic operations
+ Uncertainty propagation
+ Slicing
+ Windowing (reading and operating on subsets of data)
+ Metadata management and access

[user Manual]: https://geminidrsoftware.github.io/astrodata/manuals/usermanual/index.html
[prog manual]: https://geminidrsoftware.github.io/astrodata/manuals/progmanual/index.html

For a complete example, see the
[Quickstart](https://geminidrsoftware.github.io/astrodata/quickstart.html) in
our documentation. For more advanced usage, see the [User Manual][user manual]
or [Programmer's Manual][prog manual].

Installing development dependencies
-----------------------------------

``astrodata`` uses [Poetry](https://github.com/python-poetry/poetry) for build
and package management. Our documentation includes an [installation guide for
`astrodata`
developers](https://geminidrsoftware.github.io/astrodata/developer/index.html)

Contributing
------------

See [our contributing guidelines](CONTRIBUTING.md) for information on
contributing. If you're worried about contributing, or feel intimidated, please
remember that your contribution is immensely appreciated---no matter how small!

License
-------

This project is Copyright 2024 (c)  and licensed under the terms of a modified
BSD 3-clause license through AURA astronomy. This package is based upon the
[Openastronomy packaging
guide](https://github.com/OpenAstronomy/packaging-guide) which is licensed
under the standard BSD 3-clause license. See the LICENSE file for more
information.

Citations
---------

To cite `astrodata` in your work, please see [CITATION.md][citation link]
for complete information, including a `bibtex` example.

For ease of reference, the current citation to use is:
[Simpson et al. 2024][DRAGONS citation].

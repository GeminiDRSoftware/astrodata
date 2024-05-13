[DRAGONS link]: https://github.com/GeminiDRSoftware/DRAGONS
[astrodata docs]: https://geminidrsoftware.github.io/astrodata/
[astrodata repo]: https://geminidrsoftware.github.io/astrodata/
[astropy link]: https://astropy.org
[pypi link]: https://pypi.org/project/astrodata

[coverage badge]: https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/teald/d2f3af2a279efc1f6e90d457a3c50e47/raw/covbadge.json
[docs build badge]: https://github.com/GeminiDRSoftware/astrodata/actions/workflows/documentation.yml/badge.svg
[pypi packaging badge]: https://github.com/GeminiDRSoftware/astrodata/actions/workflows/publish_pypi.yml/badge.svg
[pypi package version badge]: https://badge.fury.io/py/astrodata.svg
[test status badge]: https://github.com/GeminiDRSoftware/astrodata/actions/workflows/testing.yml/badge.svg


`astrodata`
=============

<img align="left" src="docs/static/logo.png" height=200
style="padding-right: 10; padding-bottom: 10; border: none;">

### Tests
![A badge displaying the testing coverage percentage of this repository.][coverage badge]
![Testing status badge][test status badge]

### Building & Publishing
![Documentation build status badge][docs build badge]
[![PyPI version badge](https://badge.fury.io/py/astrodata.svg)](https://badge.fury.io/py/astrodata)
![pypi packaging status badge][pypi packaging badge]

<!-- Clearing the logo for the next header -->
<br clear="left">

Making astronomical data consistent and approachable
--------------------------------------------------------------------

`astrodata` is a package for managing astronomical data through a uniform
interface. It is designed to be used with the
[Astropy package][astropy link]. `astrodata` was designed by and
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
pip install astrodata
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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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

For a complete example, see the
[Quickstart](https://geminidrsoftware.github.io/astrodata/quickstart.html) in
our documentation.

Installing development dependencies
-----------------------------------

``astrodata`` uses [Poetry](https://github.com/python-poetry/poetry) for build
and package management. To install development dependencies, you must clone
this repository. Once you have, at the top level directory of the `astrodata`
repository run

```
pip install --upgrade pip
pip install poetry
poetry install

# To install without specific development groups. Omit those you would prefer
# not be installed
poetry install --without test,docs,dev
```

Contributing
------------

See [our contributing guidelines](CONTRIBUTING.md) for information on
contributing. If you're worried about contributing, or feel intimidated, please
remember that your contribution is immensly appreciated---no matter how small!

License
-------

This project is Copyright 2024 (c)  and licensed under the terms of a modified
BSD 3-clause license through AURA astronomy. This package is based upon the
[Openastronomy packaging
guide](https://github.com/OpenAstronomy/packaging-guide) which is licensed
under the standard BSD 3-clause licence. See the LICENSE file for more
information.

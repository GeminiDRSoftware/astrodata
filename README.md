[DRAGONS link]: https://github.com/GeminiDRSoftware/DRAGONS
[astrodata docs]: https://geminidrsoftware.github.io/astrodata/
[astrodata repo]: https://geminidrsoftware.github.io/astrodata/
[astropy link]: https://astropy.org
[pypi link]: https://pypi.org/project/astrodata

[coverage badge]: https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/teald/d2f3af2a279efc1f6e90d457a3c50e47/raw/covbadge.json
[docs build badge]: https://github.com/GeminiDRSoftware/astrodata/actions/workflows/documentation.yml/badge.svg
[pypi packaging badge]: https://github.com/GeminiDRSoftware/astrodata/actions/workflows/publish_pypi.yml/badge.svg
[test status badge]: https://github.com/GeminiDRSoftware/astrodata/actions/workflows/testing.yml/badge.svg


`astrodata`
=============

![A badge displaying the coverage level of this repository.][coverage badge]

![Tests status][test status badge]

![Documentation build status badge][docs build badge]

![pypi packaging status badge][pypi packaging badge]

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

Usage
-----

The most basic usage of ``astrodata`` is to extend the ``astrodata.AstroData``
class, which includes some basic FITS file handling methods by default:

```python
from astrodata import AstroData

class MyData(AstroData):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @astro_data_descriptor
    def my_method(self):
        print('This is my method, and it tells me about my data.')
        print(self.info())

data = MyData.read('my_file.fits')
data.my_method()
```

This will print out the header of the FITS file, as well as the filename and
path of the file (as it does for `astropy.io.fits` objects).

`astrodata` is designed to be extensible, so you can add your own methods to
analyze and process data based on your specific needs and use cases.

Documentation
-------------

Documentation for ``astrodata`` is available on our [GitHub pages site][astrodata docs]. This documentation includes a
user and programmer's guide, as well as a full API reference.


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
BSD 3-clause license. This package is based upon the [Openastronomy packaging
guide](https://github.com/OpenAstronomy/packaging-guide) which is licensed
under the standard BSD 3-clause licence. See the LICENSE file for more
information.

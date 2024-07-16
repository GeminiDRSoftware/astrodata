"""This script is used to download example files for the documentation. It is
intended to be run from the docs/examples/data directory, though .
"""

import os

import requests


def get_working_directory():
    return os.path.dirname(os.path.abspath(__file__))


def download_file(url, destination):
    with requests.get(url, stream=True) as r:
        r.raise_for_status()

        with open(destination, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)


class ExampleFiles:
    # The attributes are used to generate the directories for groups of example
    # files. Each entry should be a tuple with the name of the directory and
    # the URL to download the file (in that order).
    __slots__ = []

    quickstart = []

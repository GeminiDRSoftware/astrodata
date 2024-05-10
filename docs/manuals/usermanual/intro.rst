.. intro.rst

.. _intro_usermanual:

************
Introduction
************

Welcome to the AstroData User's Manual, a user guide for the |astrodata|
package. |astrodata| was formerly a part of the |DRAGONS| data reduction suite
developed at the Gemini Observatory. It has undergone several iteractions of
major development and improvements, and is now designed as a standalone
solution for handling astronomical data.

|astrodata| consolidates the handling of astronomical data into a single
package, using a uniform interface to access and manipulate data from
different instruments and observing modes. It is designed to be used in
conjunction with |astropy|, |numpy| and other scientific Python packages.

..
    The current chapter covers basic concepts like what is the |astrodata|
    package and how to install it (together with the other DRAGONS' packages).
    :ref:`Chapter 2 <structure>` explains with more details what is |AstroData|
    and how the data is represented using it. :ref:`Chapter 3 <iomef>`
    describes input and output operations and how multi-extension (MEF) FITS
    files are represented. :ref:`Chapter 4 <tags>` provides information
    regarding the |TagSet| class, its usage and a few advanced topics. In
    :ref:`Chapter 5 <headers>` you will find information about the FITS headers
    and how to access/modify the metadata. The last two chapters, :ref:`Chapter
    6 <pixel-data>` and :ref:`Chapter 7 <tables>` cover more details about how
    to read, manipulate and write pixel data and tables, respectively.

This introduction will guide you through the installation process and provide
a brief overview of the package. If you are looking for a quick reference,
please head to the :doc:`../cheatsheet`.

What is |astrodata|?
====================

|astrodata| is a package that wraps together tools to represent internally
astronomical datasets stored on disks and to properly parse their metadata
using the |AstroData| and the |TagSet| classes. |astrodata| provides uniform
interfaces for working on datasets from different instruments. Once a dataset
has been opened with |from_file|, the object assesses metadata to determine the
appropriate class and methods to use for reading and processing the data.
Information like instrument, observation mode, and how to access headers, is
readily available through the |AstroData| uniform interface returned by
|from_file|. All the details are coded inside the class associated with the
instrument, that class then provides the interface. The appropriate class is
selected automatically when the file is opened and inspected by |astrodata|.

Currently |astrodata| implements a basic representation for Multi-Extension
FITS (MEF) files. Extending to other file formats is possible, but requires
programming (see the |DeveloperGuide| for more information).


.. _install:

Installing Astrodata
====================

Using pip
---------

The |astrodata| package has a number of dependencies. These can be found in the
``requirements.txt`` file in the source code repository.

To install the standalone |astrodata| package, you can use pip::

        $ pip install astrodata

Or you can install it from the source code::

        $ git clone https://github.com/teald/astrodata
        $ cd astrodata # Or the directory where you cloned the repository
        $ pip install -e .

If you're interested in using |astrodata| out-of-the-box with a specific
type of data, you may want to install the astrodata package together with
their extensions. |astrodata| alone defines a base class, |AstroData|, which
is meant to be extended with instrument-specific classes. For example, to
use |astrodata| with Gemini data, you will need to install |DRAGONS|, which
includes the |astrodata| package and its extensions for |gemini_instruments|.

Source code
-----------
The source code is available on Github:

    `<https://github.com/GeminiDRSoftware/DRAGONS>`_

.. _datapkg:

A quick example
===============

Here is a quick example of how to use |astrodata| to open a file and access
its metadata using an |AstroData| object

.. code-block:: python

    >>> import astrodata
    # Create a fake file to use.
    >>> from astrodata.testing import create_test_file

    # We can create a fake file to use for this example:
    >>> path = create_test_file(include_header_keys=['INSTRUME', 'EXPTIME', 'DATE-OBS'])
    >>> ad = astrodata.from_file(path)
    >>> ad.phu['INSTRUME']
    'TEST_VALUE'

All file opening, closing and metadata management (which selects the
appropriate class for the header data) are handled by |astrodata|. There is no
need to "close" the ad object, as all file handles are closed when no longer
required or the program finishes.

.. _ad_support:

Astrodata Support
=================

Astrodata is developed and supported by staff at the Gemini Observatory.
Questions about the reduction of Gemini data should be directed to the
Gemini Helpdesk system at
`<https://noirlab.atlassian.net/servicedesk/customer/portal/12>`_.

Issues related to |astrodata| itself can be reported at our
github |IssueTracker|.

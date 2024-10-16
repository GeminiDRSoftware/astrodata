# Response

Hi all, I think I've addressed everything covered by the review. Thank you both
for your PRs, issues, and notes here. They've helped immensely so far!

I'll itemize (for ease of reference) specific response points and how I've fixed them, then summarize other changes to the code.

## Specific points (review checklist)

These are in order of reading the responses in the checklist above, with the ~sections in (parentheses).

[api_short]: https://geminidrsoftware.github.io/astrodata/api_short.html
[add_header_to_table]: https://geminidrsoftware.github.io/astrodata/api/astrodata.add_header_to_table.html
[testing docs]: https://geminidrsoftware.github.io/astrodata/developer/index.html#run-the-tests
[lint workflow]: https://github.com/GeminiDRSoftware/astrodata/blob/main/.github/workflows/lint.yml

1. (Documentation) Examples missing for user-facing functions
    1. All documentation in the ["Common API for Users"][api_short] now have examples, better explanations, or are deprecated.
    2. Specifically, [`add_header_to_table`][add_header_to_table] has been deprecated, as its functionality is no longer used. It will be removed in version 3.0.0.
    3. Covered in [PR #50](https://github.com/GeminiDRSoftware/astrodata/pull/50)
    4. The previous examples directory was a vestigial directory, and has been removed.
2. (Documentation) URLs have been added to `pyproject.toml`
    1. Commit [8f74d89](https://github.com/GeminiDRSoftware/astrodata/commit/8f74d89)
3. (Documentation/README) Badges in README now have a repostatus and Python version badge
    1. Commit [6537a51](https://github.com/GeminiDRSoftware/astrodata/commit/6537a51)
4. (Documentation/README) Citation information has been added to the README
    1. Commit [b057511](https://github.com/geminidrsoftware/astrodata/commit/b057511)
5. (Functionality/Automated tests) Testing failures
    1. All testing failures encountered were due to intermittent service with the Gemini Archive (which is getting an upgrade!), as well as some issues with Actions and their runner configurations.
    2. Tracked in [Issue #16](https://github.com/GeminiDRSoftware/astrodata/issues/16) until updates complete
6. (Functionality/Packaging Instructions) Testing instructions unclear
    1. [Developer documentation][testing docs] has been upgraded to reflect our new testing framework (using `nox`).
    2. Includes instructions for selecting specific tests, which tests are default, and specify python versions tested.
7. (Functionality/Packaging Guidelines) Repository is now linted via Actions
    1. Previously, relied on `pre-commit` alone.
    2. [New `lint.yml` workflow][lint workflow] just runs `pre-commit` to keep linting settings in `pyproject.toml`/`.pre-commit-config.yaml`
    3. Also, added `nox -s initialize_pre_commit`, automatically called by `nox -s devshell` and `nox -s devconda` to make it easier to set up the developer environment with `pre-commit`. This is still under testing.
8. (Documentation) Expanding on utility of `astrodata` in the README
    1. Include feature list and add references to manuals for futher reading alongside the Quickstart (Commit [246606d](https://github.com/geminidrsoftware/astrodata/commit/246606d)).

## Issues
All issues raised as part of the initial review have been addressed:

<details>

<summary>Issues raised as part of this review</summary>

+ [Issue #18](https://github.com/GeminiDRSoftware/astrodata/issues/18)
+ [Issue #19](https://github.com/GeminiDRSoftware/astrodata/issues/19)
+ [Issue #22](https://github.com/GeminiDRSoftware/astrodata/issues/22)
+ [Issue #23](https://github.com/GeminiDRSoftware/astrodata/issues/23)
+ [Issue #25](https://github.com/GeminiDRSoftware/astrodata/issues/25)
+ [Issue #26](https://github.com/GeminiDRSoftware/astrodata/issues/26)
+ [Issue #27](https://github.com/GeminiDRSoftware/astrodata/issues/27)
+ [Issue #28](https://github.com/GeminiDRSoftware/astrodata/issues/28)
+ [Issue #29](https://github.com/GeminiDRSoftware/astrodata/issues/29)
+ [Issue #33](https://github.com/GeminiDRSoftware/astrodata/issues/33)

</details>

## Pull Requests

All PRs have been merged into the main code:

<details>

<summary>List of Pull Requests made by reviewers</summary>

+ [Pull Request #20](https://github.com/GeminiDRSoftware/astrodata/pull/20)
+ [Pull Request #21](https://github.com/GeminiDRSoftware/astrodata/pull/21)

</details>

Thank you for your contributions!

<details>

<summary>List of Pull Requests related to this review.</summary>

+ [Pull Request #24](https://github.com/GeminiDRSoftware/astrodata/pull/24)
+ [Pull Request #31](https://github.com/GeminiDRSoftware/astrodata/pull/31)
+ [Pull Request #32](https://github.com/GeminiDRSoftware/astrodata/pull/32)
+ [Pull Request #34](https://github.com/GeminiDRSoftware/astrodata/pull/34)
+ [Pull Request #38](https://github.com/GeminiDRSoftware/astrodata/pull/38)
+ [Pull Request #41](https://github.com/GeminiDRSoftware/astrodata/pull/41)
+ [Pull Request #46](https://github.com/GeminiDRSoftware/astrodata/pull/46)
+ [Pull Request #48](https://github.com/GeminiDRSoftware/astrodata/pull/48)
+ [Pull Request #50](https://github.com/GeminiDRSoftware/astrodata/pull/50)
+ [Pull Request #51](https://github.com/GeminiDRSoftware/astrodata/pull/51)
+ [Pull Request #53](https://github.com/GeminiDRSoftware/astrodata/pull/53)

</details>


## Other changes of note

[devshells]: https://geminidrsoftware.github.io/astrodata/developer/index.html#install-the-dependencies
[poetry devs]: https://geminidrsoftware.github.io/astrodata/developer/index.html#install-the-dependencies
[test docs]: https://geminidrsoftware.github.io/astrodata/developer/index.html#run-the-tests

1. We've moved from using `tox` for testing to `nox` for testing and general automation. This was already planned for after this review to better support `conda` testing, but it made more sense to get this done now.
2. The developer documentation has been overhauled to describe several new development features motivated by these reviews:
    1. [Automated development environment creation][devshells]
    2. [Developing without a virtual environment][poetry devs]
    3. [Clearer testing documentation][test docs]

## Responses to reviewer comments

### mwcraig

**1. What is your conception of how this should interact with the rest of the ecosystem (thinking mostly about nddata and ccdproc here)?**

`astrodata` uses `astropy.nddata` for most of its core arithmetic functionality, including a number of the same, or slightly modified, mixins. There are likely some points of consolidation (see below) between the two that may happen. As for ccdproc, I think with `CCDData` already inheriting `NDDataArray` (which is similar to `NDAstroData`), there are opportunities for integration there. I would need to spend some more time thinking about that and looking at source, though.

Since `astrodata` provides support for MEF, as you pointed out in another question, as well as meta-data abstraction that is closely tied to the representation of the data compared to other tools, this streamlines the process of associating data and metadata from a user perspective. Users do not have to worry about managing the overhead that arises from handling lists of files and metadata tables. The descriptors provide a standardized way to create generic processing tools that hide boilerplate from the user, and tags allow for organization based on metadata properties or other traits of the data.

**2. Does it make sense to upstream any of this (like the arithmetic handling or allowing for any WCS, not just an astropy.wcs) to astropy.nddata? Or to ccdproc?**

There are plans to upstream some of the work done in the astrodata.wcs module to gwcs, specifically regarding the conversion between gwcs objects and their representation as FITS keywords, and then use gwcs throughout astrodata. But, that work hasn't been started yet and it's not clear when the resources will be available. I think that's probably the better avenue for more generic WCS support than `astropy.nddata`.

As mentioned above, I think there are some good opportunities for taking some of the handling done by `astrodata` and integrating it into, e.g., `CCDData`, where `astrodata.AstroData` objects naturally fit into the existing `NDDataArray` dependencies. I'm sure there are nuances there that would need to be sorted, but I could see `CCDData`/ccdproc using some of the features of `astrodata` to enhance their current functionality.

We could also consider how `astrodata` might assist/impact the goals of the closed [APE 11](https://github.com/astropy/astropy-APEs/pull/14). However, I think that'd require larger-scale coordination after this review has concluded (as part of [APE PR #100](https://github.com/astropy/astropy-APEs/issues/100)).

**3. Does it make sense for ccdproc to depend on astrodata or try to integrate usage of astrodata into it? ccdproc has never had a good way of handling MEF files, which is faintly ridiculous (I'm the maintainer of ccdproc so I'm looking in the mirror rather throwing stones here).**

It depends on the goals of ccdproc moving forward. For MEFs it's feasible to break images up from a list into individual images ccdproc can then process. `astrodata` may, at the end of the day, be excessive for the work ccdproc does in its current scope.

**4. My take is that astrodata provides a way to abstract images and metadata from the underlying way they are stored, which is something that none of the current tools that I'm aware of provide. It may very well not make sense to upstream any of this.**

I think the biggest consideration is whether resources required to make these changes are worth the benefits themselves. There are natural places where `astrodata`'s abstraction would help generalize/make other Astropy packages more flexible.

Right now, though, the work required to share data between, e.g., `astrodata`, `astropy.nddata`, and ccdproc is straightforward but requires some management between them that could be reduced to utility methods. I wrote up a quick, simple example to see how working with both `astrodata` and `ccdproc` went:

<details>

<summary>Code example working with astrodata and ccdproc</summary>

```python
from astrodata import AstroData, create
from astropy.nddata import CCDData, NDData
from astropy.io import fits
import astropy.units as u
import numpy as np
import ccdproc

# Create a simple FITS file object with data and a header:
hdu = fits.PrimaryHDU(data=np.ones((100, 100)))
hdu.header["INSTRUME"] = "random_inst"
hdu.header["MODE"] = "random_mode"
hdu.header["UNIT"] = "adu"
hdu.header["EXPTIME"] = 5.0

# Create an AstroData object from the FITS file object:
ad = create(hdu)

# Access the underlying data and create a CCDData object:
ccd_image = CCDData(data=ad[0].data, unit=ad[0].hdr["UNIT"], meta=ad[0].hdr)

# Create a dark frame with the same shape as the data:
hdu_dark = fits.PrimaryHDU(data=np.random.random((100, 100)) * 10)
hdu_dark.header["INSTRUME"] = "random_inst"
hdu_dark.header["MODE"] = "random_dark_mode"
hdu_dark.header["UNIT"] = "adu"
hdu_dark.header["EXPTIME"] = 10.0

# Create an AstroData object from the FITS file object:
ad_dark = create(hdu_dark)

# Access the underlying data and create a CCDData object:
dark = CCDData(
    ad_dark[0].data,
    unit=ad_dark[0].hdr["UNIT"],
    meta=ad_dark[0].hdr,
)

# Subtract the dark frame from the data:
ccd_dark_subtracted = ccdproc.subtract_dark(
    ccd_image,
    dark,
    dark_exposure=dark.header["EXPTIME"] * u.s,
    data_exposure=ccd_image.header["EXPTIME"] * u.s,
)

```

</details>

This is a pretty minimal example, of course, but I think cases where the two interact can be managed primarily through accessing underlying data and metadata directly, rather than creating outright support for `astrodata` within the other packages.

**5. Would it be possible to provide a small example of how to develop a processing tool with astrodata that goes beyond just adding properties and tags? In otherwords, once I have done those things what does astrodata do for me? I'm not suggesting a full reduction pipeline here (DRAGONS does that) but something that shows a step or two of processing files using would be helpful.**

This is still being worked on. I'd like this example to be relatively complete in overview of how `astrodata` works, and I've been taking time coming up with something suitable. I think it's unavoidable to have it be somewhat complex, since `astrodata` and the properties and tags drive much of what users and developers will commonly interact with.

[example issue]: https://github.com/GeminiDRSoftware/astrodata/issues/57

Development is being tracked in [this issue][example issue]. For now, the User Manual and Programmer's manuals have a bit more in-depth explanation, though I agree a more concrete, featureful example would be ideal.

### aaryapatil

Thank you for your review and feedback! Let me know if you have any further questions or comments.

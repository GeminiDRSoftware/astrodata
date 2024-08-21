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

<!-- TODO: <details> & <summary> for this section -->

1. (Documentation) Examples missing for user-facing functions
    1. All documentation in the ["Common API for Users"][api_short] now
    have examples, better explanations, or are deprecated.
    2. Specifically, [`add_header_to_table`][add_header_to_table] has been deprecated, as its functionality is no longer used. It will be removed in version 3.0.0.
    3. Covered in PR #50
    4. The previous examples directory was a vestigial directory, and has been removed.
2. (Documentation) URLs have been added to `pyproject.toml`
    1. Commit 8f74d89
3. (Documentation/README) Badges in README now have a repostatus and Python version badge
    1. Commit 6537a51
4. (Documentation/README) Citation information has been added to the README
    1. Commit b057511
5. (Functionality/Automated tests) Testing failures
    1. All testing failures encountered were due to intermittent service with the Gemini Archive (which is getting an upgrade!), as well as some issues with Actions and their runner configurations.
    2. Tracked in Issue #16 until updates complete
6. (Functionality/Packaging Instructions) Testing instructions unclear
    1. [Developer documentation][testing docs] has been upgraded to reflect our new testing framework (using `nox`).
    2. Includes instructions for selecting specific tests, which tests are default, and specify python versions tested.
7. (Functionality/Packaging Guidelines) Repository is now linted via Actions
    1. Previously, relied on `pre-commit` alone.
    2. [New `lint.yml` workflow][lint workflow] just runs `pre-commit` to keep linting settings in `pyproject.toml`/`.pre-commit-config.yaml`
    3. Also, added `nox -s initialize_pre_commit`, automatically called by `nox -s devshell` and `nox -s devconda` to make it easier to set up the developer environment with `pre-commit`. This is still under testing.
8. (Documentation) Expanding on utility of `astrodata` in the README
    1. TKTODO

## Issues
All issues raised as part of the initial review have been addressed:
<details>

<summary>Issues raised as part of this review</summary>

+ Issue #18
+ Issue #19
+ Issue #22
+ Issue #23
+ Issue #25
+ Issue #26
+ Issue #27
+ Issue #28
+ Issue #29
+ Issue #33

</details>

## Pull Requests

All PRs have been merged into the main code:

<details>

<summary>List of Pull Requests made as part of this review</summary>

+ Pull Request #20
+ Pull Request #21

</details>

Thank you for your contributions!

## Other changes of note

[devshells]: https://geminidrsoftware.github.io/astrodata/developer/index.html#install-the-dependencies
[poetry devs]: https://geminidrsoftware.github.io/astrodata/developer/index.html#install-the-dependencies
[test docs]: https://geminidrsoftware.github.io/astrodata/developer/index.html#run-the-tests

1. We've moved from using `tox` for testing to `nox` for testing and general
automation. This was already planned for after this review to better support
`conda` testing, but it made more sense to get this done now.
2. The developer documentation has been overhauled to describe several new
development features motivated by these reviews:
    1. [Automated development environment creation][devshells]
    2. [Developing without a virtual environment][poetry devs]
    3. [Clearer testing documentation][test docs]

## Responses to reviewer comments

### mwcraig

### aaryapatil

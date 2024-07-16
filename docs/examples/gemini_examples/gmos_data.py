"""Example of using GMOS' implementation of astrodata to read, display, and
manipulate a GMOS image.

This example demonstrates how to:
    - Read a GMOS image
    - Display the image
    - Display the image with a mask overlay
    - Display the image with a mask overlay and a custom color map

In order to run this example, you will need an internet connection and the
following packages installed:
    - gemini_instruments
    - matplotlib
    - numpy
    - astrodata

Along with their associated dependencies.

If you would like to have an environment with all these dependencies installed,
you can create a conda environment with the provided environment.yml in the
same directory as this example. To do so, you can run the following command in
your terminal:

.. code-block::terminal

    # Solving this environment may take some time.
    conda env create -f astrodata_gemini_examples.yml
    conda activate astrodata_gemini_examples

    # NOTE: You also must install a local version of astrodata if you are
    #       running this example from a local repository. If you are
    #       just running this example on its own, you can use the
    #       astrodata package from the conda-forge channel and skip the next
    #       command.
    pip install -e "<PATH TO ASTRODATA TOP DIR HERE>[all]"

After creating the environment, you can activate it by running:

.. code-block::terminal

        conda activate astrodata_gemini_examples

Then you can run this example by executing it directly.
"""

from astrodata.testing import download_from_archive
import astrodata

# Download the example data
filename = download_from_archive(
    "N20180115S0336.fits",
    path="./example_data",
    sub_path="",
)

# At this point, all the necessary packages should be installed, and the
# gemini_instruments package has registered the GMOS instrument with Astrodata.
# Now, when we make an AstroData object, it will be an instance of
# gemini_instruments.gmos.adclass.AstroDataGmos.
ad = astrodata.open(filename)

# We can now manipulate the data and access it as we would for any other
# AstroData object, plus some specific GMOS functionality. For example, we can
# display the image with a mask overlay and a custom color map.
import matplotlib.pyplot as plt  # noqa: E402


image = ad[0].data
im = plt.imshow(image, cmap="gray")

plt.show()

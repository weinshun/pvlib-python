.. image:: _images/pvlib_logo_horiz.png
  :width: 600

pvlib python
============

pvlib python is a community developed toolbox that provides a set of
functions and classes for simulating the performance of photovoltaic
energy systems and accomplishing related tasks.
The core mission of pvlib python is to provide open,
reliable, interoperable, and benchmark implementations of PV system models.

The source code for pvlib python is hosted on `github
<https://github.com/pvlib/pvlib-python>`_.
Please see the :ref:`installation` page for installation help.

For examples of how to use pvlib python, please see
:ref:`package_overview` and our `Jupyter Notebook tutorials
<http://nbviewer.org/github/pvlib/pvlib-python/tree/main/docs/
tutorials/>`_. The documentation assumes general familiarity with
Python, NumPy, and Pandas. Google searches will yield many
excellent tutorials for these packages.

The pvlib python GitHub wiki has a `Projects and publications that use
pvlib python
<https://github.com/pvlib/pvlib-python/wiki/Projects-and-publications-
that-use-pvlib-python>`_ page for inspiration and listing of your
application.

There is a :ref:`variable naming convention <variables_style_rules>` to
ensure consistency throughout the library.


History and acknowledgement
===========================

pvlib python started out as a Python translation of the PVLIB MATLAB
toolbox (developed by the `PVPMC <https://pvpmc.sandia.gov/>`_ at
Sandia National Laboratories) in 2013 and has grown substantially since then.
Today it contains code contributions from over a hundred individuals worldwide
and is maintained by a core group of PV modelers from a variety institutions.

pvlib has been supported directly and indirectly by DOE, NumFOCUS, and
Google Summer of Code funding, university research projects,
companies that allow their employees to contribute, and from personal time.


Citing pvlib python
===================

Many of the contributors to pvlib python work in institutions where
citation metrics are used in performance or career evaluations. If you
use pvlib python in a published work, please cite:

**Recommended citation for the pvlib python project**

  Anderson, K., Hansen, C., Holmgren, W., Jensen, A., Mikofski, M., and Driesse, A.
  "pvlib python: 2023 project update."
  Journal of Open Source Software, 8(92), 5994, (2023).
  https://doi.org/10.21105/joss.05994


**Recommended citation for pvlib iotools**

  Jensen, A., Anderson, K., Holmgren, W., Mikofski, M., Hansen, C., Boeman, L., Loonen, R.
  "pvlib iotools — Open-source Python functions for seamless access to solar irradiance data."
  Solar Energy, 266, 112092, (2023).
  https://doi.org/10.1016/j.solener.2023.112092

**Historical citation for pvlib python**

  Holmgren, W., Hansen, C., and Mikofski, M.
  "pvlib python: a python package for modeling solar energy systems."
  Journal of Open Source Software, 3(29), 884, (2018).
  https://doi.org/10.21105/joss.00884

**Version specific citation**
Please also cite the DOI corresponding to the specific version of
pvlib python that you used. pvlib python DOIs are listed at
`Zenodo.org <https://zenodo.org/search?page=1&size=20&q=conceptrecid:593284&all_versions&sort=-version>`_


Additional pvlib python publications include:

* J. S. Stein, “The photovoltaic performance modeling
  collaborative (PVPMC),” in Photovoltaic Specialists Conference, 2012.
* R.W. Andrews, J.S. Stein, C. Hansen, and D. Riley, “Introduction
  to the open source pvlib for python photovoltaic system
  modelling package,” in 40th IEEE Photovoltaic Specialist
  Conference, 2014.
  (`paper
  <http://energy.sandia.gov/wp/wp-content/gallery/uploads/PV_LIB_Python_final_SAND2014-18444C.pdf>`__)
* W.F. Holmgren, R.W. Andrews, A.T. Lorenzo, and J.S. Stein,
  “PVLIB Python 2015,” in 42nd Photovoltaic Specialists Conference, 2015.
  (`paper
  <https://github.com/pvlib/pvsc2015/blob/main/pvlib_pvsc_42.pdf>`__ and
  the `notebook to reproduce the figures
  <http://nbviewer.org/github/pvlib/pvsc2015/blob/main/paper.ipynb>`_)
* J.S. Stein, W.F. Holmgren, J. Forbess, and C.W. Hansen,
  "PVLIB: Open Source Photovoltaic Performance Modeling Functions
  for Matlab and Python," in 43rd Photovoltaic Specialists Conference, 2016.
* W.F. Holmgren and D.G. Groenendyk,
  "An Open Source Solar Power Forecasting Tool Using PVLIB-Python,"
  in 43rd Photovoltaic Specialists Conference, 2016.


Logo
====
If you use pvlib python in a commercial or publicly-available
application, please consider displaying one of the "powered by pvlib"
logos:

.. image:: _images/pvlib_powered_logo_horiz.png
  :width: 300

.. image:: _images/pvlib_powered_logo_vert.png
  :width: 300

License
=======

`BSD 3-clause <https://github.com/pvlib/pvlib-python/blob/main/LICENSE>`_.

NumFOCUS
========

pvlib python is a `NumFOCUS Affiliated Project <https://numfocus.org/sponsored-projects/affiliated-projects>`_

.. image:: https://i0.wp.com/numfocus.org/wp-content/uploads/2019/06/AffiliatedProject.png
  :target: https://numfocus.org/sponsored-projects/affiliated-projects
  :alt: NumFocus Affliated Projects

.. toctree::
   :maxdepth: 1
   :hidden:

   user_guide/index
   gallery_examples/index
   gallery_tutorials/index
   reference/index
   whatsnew
   contributing

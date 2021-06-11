HERON regulatory enforcement web interface
******************************************

The Healthcare Enterprise Repository for Ontological Narration (HERON)
is a method to integrate clinical and biomedical data for
translational research. The bulk of the functionality is provided by
i2b2__; this code is the regulatory enforcement web interface.

__ https://www.i2b2.org/

:Copyright: Copyright 2010-2019 University of Kansas Medical Center


Usage
-----

To start a server in development mode, follow `pyramid norms`__ (with
python2.7 rather than python3)::

  cd heron-admin
  virtualenv env
  ./env/bin/pip install -e ".[testing]"
  # Reset our environment variable for a new virtual environment.
  export VENV=~/heron_admin/env

 -- if runnig with python3
  cd heron-admin
  python3 -m venv env
  env/bin/pip install --upgrade pip setuptools
  env/bin/pip install -e . OR ./env/bin/pip install -e ".[testing]"
  ... more steps to come

  $VENV/bin/pserve development.ini

__ https://docs.pylonsproject.org/projects/pyramid/en/1.10-branch/quick_tour.html

In production, more `extensive configuration`__ is required.

__ https://bmi-work.kumc.edu/work/wiki/GroupOnly/HeronAdmin


Testing, Design, Development
----------------------------

See `setup.py`, `devdoc` for details.


Citing HERON
------------

Please cite us as:

  * Waitman LR, Warren JJ, Manos EL, Connolly DW.  `Expressing
    Observations from Electronic Medical Record Flowsheets in an i2b2
    based Clinical Data Repository to Support Research and Quality
    Improvement`__.  AMIA Annu Symp Proc. 2011;2011:1454-63. Epub 2011
    Oct 22.

__ http://www.ncbi.nlm.nih.gov/pmc/articles/PMC3243191/


AMIA CRI Poster with Screenshots
================================

  * Tamara M. McMahon, Daniel W. Connolly, Bhargav Adagarla,
    Lemuel R. Waitman. `Role of Informatics Coordinator in Catalyzing
    Adoption of a Self-Service Integrated Data Repository Model`__
    AMIA 2014 Summit on Clinical Research Informatics
    
__ http://frontiersresearch.org/frontiers/sites/default/files/frontiers/AMIA2014CRI-McMahonFinal.pdf


Acknowledgements
----------------

This work was supported by a CTSA grant from NCRR and NCATS__ awarded
to the University of Kansas Medical Center for `Frontiers: The
Heartland Institute for Clinical and Translational Research`__ #
UL1TR000001 (formerly #UL1RR033179). The contents are solely the
responsibility of the authors and do not necessarily represent the
official views of the NIH, NCRR, or NCATS.

__ http://www.ncats.nih.gov/
__ http://frontiersresearch.org/

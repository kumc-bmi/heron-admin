HERON regulatory enforcement web interface
******************************************

The Healthcare Enterprise Repository for Ontological Narration (HERON)
is a method to integrate clinical and biomedical data for
translational research. The bulk of the functionality is provided by
i2b2__; this code is the regulatory enforcement web interface.

__ https://www.i2b2.org/

:Copyright: Copyright 2010-2015 University of Kansas Medical Center

**todo** administrative interface: POST to re-read config files

Development dependencies
------------------------

See `setup.py` for details.

Object Capability Style and Dependency Injection
------------------------------------------------

* `Dependency Injection Myth: Reference Passing`__ Oct 2008 by Miško
  Hevery, an Agile Coach at Google where he is responsible for
  coaching Googlers to maintain the high level of automated testing
  culture. It motivates passing in any source of non-determinism as
  a constructor arg, for testability. See also:

     * `Guide: Writing Testable Code`__
     *  `Video Recording & Slides: Psychology of Testing at Wealthfront Engineering`__ Feb 2011

__ http://misko.hevery.com/2008/10/21/dependency-injection-myth-reference-passing/
__ http://misko.hevery.com/code-reviewers-guide/
__ http://misko.hevery.com/2011/02/14/video-recording-slides-psychology-of-testing-at-wealthfront-engineering/

* `Security of emakers`__ motivates passing in any source of authority
  (and any source of non-determinism seems to be a source of authority)
  as a constructor arg.

__ http://wiki.erights.org/wiki/Walnut/Ordinary_Programming#Security_of_emakers

Citing HERON
------------

Please cite us as:

  * Waitman LR, Warren JJ, Manos EL, Connolly DW.  `Expressing
    Observations from Electronic Medical Record Flowsheets in an i2b2
    based Clinical Data Repository to Support Research and Quality
    Improvement`__.  AMIA Annu Symp Proc. 2011;2011:1454-63. Epub 2011
    Oct 22.

__ http://www.ncbi.nlm.nih.gov/pmc/articles/PMC3243191/


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

HERON regulatory enforcement web interface
******************************************

The Healthcare Enterprise Repository for Ontological Narration (HERON)
is a method to integrate clinical and biomedical data for
translational research. The bulk of the functionality is provided by
i2b2__; this code is the regulatory enforcement web interface.

__ https://www.i2b2.org/


**todo** administrative interface: POST to re-read config files

Development dependencies
------------------------

See setup.py for details.

Object Capability Style and Dependency Injection
------------------------------------------------

* `Dependency Injection Myth: Reference Passing`__ Oct 2008 by Miško
   Hevery, an Agile Coach at Google where he is responsible for
   coaching Googlers to maintain the high level of automated testing
   culture. It motivates passing in any source of non-determinism as
   a constructor arg, for testability.
   See also
   * `Guide: Writing Testable Code`__
   *  `Video Recording & Slides: Psychology of Testing at Wealthfront Engineering`__ Feb 2011

__ http://misko.hevery.com/2008/10/21/dependency-injection-myth-reference-passing/
__ http://misko.hevery.com/code-reviewers-guide/
__ http://misko.hevery.com/2011/02/14/video-recording-slides-psychology-of-testing-at-wealthfront-engineering/

* `Security of emakers`__ motivates passing in any source of authority (and any source
   of non-determinism seems to be a source of authority) as a constructor arg.

__ http://wiki.erights.org/wiki/Walnut/Ordinary_Programming#Security_of_emakers

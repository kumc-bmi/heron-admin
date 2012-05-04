HERON regulatory enforcement web interface
******************************************

The Healthcare Enterprise Repository for Ontological Narration (HERON)
is a method to integrate clinical and biomedical data for
translational research. The bulk of the functionality is provided by
i2b2__; this code is the regulatory enforcement web interface.

__ https://www.i2b2.org/


how to run... failure modes...

genshi template language:
http://genshi.edgewall.org/wiki/Documentation/xml-templates.html
http://genshi.edgewall.org/wiki/GenshiTutorial

pyramid, paste, wsgi@@@
python setup.py develop@@@
$ python heron_srv.py localhost 8123

medcenter.py
ConfigParser.NoSectionError: No section: 'enterprise_directory'
need config file; see .example

urllib2.URLError: <urlopen error [Errno 111] Connection refused>
need chalk checker Java app running; use an ssh tunnel; see .example

disclaimer.py
sqlalchemy.exc.OperationalError: (OperationalError) (2003, "Can't connect to MySQL server on '127.0.0.1' (111)") None None

see section [redcapdb]@@...


heron_wsgi - the python approach

.. todo:: administrative interface: POST to re-read config files

.hgignore - stuff to ignore from version control (e.g. maven's target/)


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


injector gotchas
................

When you see this::

    Traceback (most recent call last):
      File "/home/dconnolly/raven-frontiers/heron_wsgi/admin_lib/heron_policy.py", line 433, in make_stuff
        hr = depgraph.get(HeronRecords)
    ...
      File "build/bdist.linux-x86_64/egg/injector.py", line 467, in provider_for
        elif isinstance(to, interface):
    TypeError: isinstance() arg 2 must be a class, type, or tuple of classes and types

Look for one of the constructor args to HeronRecords that isn't bound.


Java Approach
-------------

This repository is a mixure of a java approach and a python approach.

following Java/eclipse norms, we have:

 - src
 - .classpath
 - .pmd
 - .project
 - .settings
 - .wtpmodules
 - pom.xml - maven package object model (build file)

We also have:

apache-conf - proxy configuration for the Java approach

apache-conf-raven - mod_wsgi configuration for the python approach


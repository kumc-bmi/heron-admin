Code Quality: Style, Testing
----------------------------

We aim to use `nose`__ (with `doctest`__), and `flake8`__ to automate
testing and enforce python community norms for style.  (See
`../test/runtests.sh` for a work-around for an issue with nose and
doctest.)

The `import grouping guideline`__ is not enforced mechanically:

    Imports should be grouped in the following order:

      1.  Standard library imports.
      2.  Related third party imports.
      3.  Local application/library specific imports.

__ https://tox.readthedocs.io/en/latest/
__ https://nose.readthedocs.io/en/latest/
__ https://docs.python.org/2.7/library/doctest.html
__ http://flake8.pycqa.org/en/latest/
__ https://www.python.org/dev/peps/pep-0008/#imports


Integration Testing
...................

In addition to unit tests, it's convenient if each module can be
integration-tested by running it as a script; for example::

  $ cd heron_wsgi/admin_lib
  $ python heron_admin.py
  Traceback (most recent call last):
    ...
    File "heron_policy.py", line 877, in _script
      userid, config_fn = argv[1:3]
  ValueError: need more than 0 values to unpack

  $ python heron_policy.py dconnolly integration-test.ini
  INFO:traincheck.traincheck:HSR DB name: hsr_cache
  INFO:medcenter:testing faculty: []
  INFO:cache_remote:LDAPService@1 cache initialized
  ...

Note the `userid, config_fn = argv[1:3]` argument parsing idiom so
that the traceback serves as quick-n-dirty usage documentation.

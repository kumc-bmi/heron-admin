Code Quality: Style, Testing
----------------------------

We use `tox`__, `nose`__ (with `doctest`__), and `flake8`__ to
automate testing and enforce python community norms for style.

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

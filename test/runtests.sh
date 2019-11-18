#/bin/bash

set -e

# run test from top dir of project
cd $(dirname $0)/..

# ISSUE: doctests with dicts are fragile
export  PYTHONHASHSEED=100
# ISSUE: help stats.py find genshi_render.py
export PYTHONPATH=heron_wsgi

# ISSUE: heron_srv doctests are failing with:
# AppError: Bad response: 303 See Other (not 200)
# nosetests --with-doctest
# So we run them separately:
pipenv run nosetests --with-doctest heron_wsgi/admin_lib

# $ ls -1 heron_wsgi/*.py | while read py; do echo "    python -m doctest $py"; done
pipenv run python -m doctest heron_wsgi/__init__.py
pipenv run python -m doctest heron_wsgi/cas_auth.py
pipenv run python -m doctest heron_wsgi/drocnotice.py
pipenv run python -m doctest heron_wsgi/genshi_render.py
pipenv run python -m doctest heron_wsgi/heron_srv.py
pipenv run python -m doctest heron_wsgi/perf_reports.py
pipenv run python -m doctest heron_wsgi/stats.py

# see setup.cfg for coding style info
pipenv run flake8 heron_wsgi

# Detection of Security Vulnerabilities
# https://pipenv.readthedocs.io/en/latest/advanced/#detection-of-security-vulnerabilities
pipenv check

pipenv run python setup.py sdist

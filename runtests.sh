# This is a horrible kludge.
# Doctests were originally developed by running one file at a time a la:
#   python -m doctest heron_srv.py
# When run under nosetests, they don't quite work. So...

set -e

# use dirname $0?
pkg=`/bin/pwd`
export PYTHONPATH=$pkg:$pkg/heron_wsgi:$pkg/heron_wsgi/admin_lib

cd heron_wsgi
for src in *.py; do echo $src; python -m doctest $src; done

cd admin_lib
for src in *.py; do echo $src; python -m doctest $src; done

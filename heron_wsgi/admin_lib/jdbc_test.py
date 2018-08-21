'''jdbc_test -- JDBC integration test

Usage:

  jython -J-cp .../sqlite-jdbc-3.21.0.1.jar jdbc_test.py

To get the path to the sqlite JDBC jar, use:

  ./gradlew showClassPath

'''

from __future__ import print_function
from sys import stderr  # ocap note: tracing exception

import org.sqlite.JDBC
from jaydebeapi import paramstyle, Error, ProgrammingError


def sqlite_memory_engine(echo=False):
    return _dbi_engine('sqlite://', module=_SqliteJDBC, echo=echo)


class _SqliteJDBC(object):
    """Provide DBI "module" that ignores the sqlite path given by
    SQLAlchemy.

    """
    paramstyle = paramstyle

    Error = Error
    ProgrammingError = ProgrammingError

    # ISSUE: jar version is 3.21.0.1; use something based on that?
    # python 2.7.12 on Ubuntu 16.04
    sqlite_version_info = version_info = (3, 11, 0)

    memory_url = "jdbc:sqlite::memory:"

    @classmethod
    def connect(cls, _db):
        conn = _sqlite_memory_conn()
        conn.jconn.setAutoCommit(False)
        return conn


def _sqlite_memory_conn():
    # In general, connect has ambient authority,
    # but using `memory_url` avoids it.
    from jaydebeapi import connect
    return connect(org.sqlite.JDBC.getName(), _SqliteJDBC.memory_url)


def _dbi_engine(url, module,
                echo=False):
    """Create an SQLAlchemy engine from a DB API module.
    """
    # In general, create_engine has ambient authority,
    # but supplying the DB API module overrides it.
    from sqlalchemy import create_engine
    return create_engine(url, module=module, echo=echo)


if __name__ == '__main__':
    e = sqlite_memory_engine()
    [sum] = e.execute('select 1+1').fetchone()
    print(sum, file=stderr)

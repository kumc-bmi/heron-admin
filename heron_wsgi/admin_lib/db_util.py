'''
'''

from contextlib import contextmanager

import cx_Oracle
import MySQLdb # http://mysql-python.sourceforge.net/MySQLdb.html#mysqldb

def oracle_connect(u, p, host, port, sid):
    dsn = cx_Oracle.makedsn(host, port, sid)
    return cx_Oracle.connect(dsn=dsn, user=u, password=p)


def mysql_connect(u, p, host, port, db):
    return MySQLdb.connect(host=host, user=u, passwd=p, port=port, db=db)


@contextmanager
def transaction(conn):
    '''Return an Oracle database cursor manager.

    :param conn: an Oracle connection
    '''
    c = conn.cursor()
    try:
        yield c
    except cx_Oracle.DatabaseError:
        conn.rollback()
        raise
    else:
        conn.commit()
    finally:
        c.close()

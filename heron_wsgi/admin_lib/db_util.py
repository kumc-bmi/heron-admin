'''
'''

from contextlib import contextmanager

def oracle_connect(u, p, host, port, sid):
    import cx_Oracle
    dsn = cx_Oracle.makedsn(host, port, sid)
    return cx_Oracle.connect(dsn=dsn, user=u, password=p)


def mysql_connect(u, p, host, port, db):
    import MySQLdb # http://mysql-python.sourceforge.net/MySQLdb.html#mysqldb
    return MySQLdb.connect(host=host, user=u, passwd=p, port=port, db=db)


@contextmanager
def transaction(conn):
    '''Return an database cursor manager.

    :param conn: an Oracle connection
    '''
    c = conn.cursor()
    try:
        yield c
    except IOError:
        conn.rollback()
        raise
    else:
        conn.commit()
    finally:
        c.close()

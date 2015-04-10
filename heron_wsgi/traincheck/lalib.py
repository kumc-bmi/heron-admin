'''ladb -- least-authority style database access

.. note: cribbed from pcori_load.py from gpc-pcornet-cdm
         Mar 17 2b34bc7b71b1
'''

from contextlib import contextmanager
from posixpath import basename, splitext, join


def maker(wrapped):
    def make(*args, **kwargs):
        methods, properties = wrapped(*args, **kwargs)
        bases = (object,)
        maker = type(wrapped.__name__, bases,
                     dict(properties.items() +
                          [(m.__name__, m) for m in methods]))
        return maker()
    return make


@maker
def Rd(path, open_rd, listdir):
    def __div__(_, sub):
        fullsub = join(path, sub)
        if not fullsub.startswith(path):
            raise IOError('no upward traversal')

        return Rd(fullsub, open_rd, listdir)

    def open(_):
        return open_rd(path)

    def iterdir(_):
        return (Rd(join(path, p), open_rd, listdir)
                for p in listdir(path))

    return [__div__, open, iterdir], dict(
        name=basename(path),
        suffix=splitext(path)[1])


def dbmgr(connect):
    '''Make a context manager that yields cursors, given connect access.
    '''
    @contextmanager
    def dbtrx():
        conn = connect()
        cur = conn.cursor()
        try:
            yield cur
        except:
            conn.rollback()
            raise
        else:
            conn.commit()
        finally:
            cur.close()
    return dbtrx

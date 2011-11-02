
import injector
from injector import inject
from sqlalchemy.orm.session import Session

import i2b2pm

class Migration(object):
    @inject(smaker=(Session, i2b2pm.CONFIG_SECTION))
    def __init__(self, smaker):
        self._smaker = smaker

    def dump_something(self):
        s = self._smaker()
        ans = s.execute('select * from heron.system_access_users')
        return ans.fetchall()

if __name__ == '__main__':
    from pprint import pprint

    depgraph = i2b2pm.RunTime.depgraph()
    mi = depgraph.get(Migration)
    pprint(mi.dump_something())


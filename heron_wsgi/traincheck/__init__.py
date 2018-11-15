# "The __init__.py files are required to make Python treat the
# directories as containing packages"
# -- http://docs.python.org/tutorial/modules.html

from ConfigParser import ConfigParser

from sqlalchemy.engine.url import make_url

from traincheck import TrainingRecordsRd

TRAINING_SECTION = 'training'


def from_config(ini, create_engine):
    cp = ConfigParser()
    cp.readfp(ini.open(), str(ini))
    u = make_url(cp.get(TRAINING_SECTION, 'url'))
    redcapdb = (None if u.drivername == 'sqlite' else 'redcap')

    # Address connection timeouts using pool_recycle
    # ref http://docs.sqlalchemy.org/en/rel_1_0/dialects/mysql.html#connection-timeouts  # noqa
    trainingdb = create_engine(u, pool_recycle=3600)
    account = lambda: trainingdb.connect(), u.database, redcapdb

    tr = TrainingRecordsRd(account)

    return tr.__getitem__

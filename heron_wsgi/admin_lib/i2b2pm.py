'''i2b2pm -- I2B2 Project Management cell client/proxy

Ensure account sets up the DB as the I2B2 project manager expects::

  >>> pm, depgraph = Mock.make([I2B2PM, None])
  >>> pm.ensure_account('john.smith')

  >>> import pprint
  >>> dbsrc = depgraph.get((Session, CONFIG_SECTION))
  >>> ans = dbsrc().execute('select project_id, user_id, '
  ...                       ' user_role_cd, status_cd'
  ...                       ' from pm_project_user_roles')
  >>> pprint.pprint(ans.fetchall())
  [(u'BlueHeron', u'john.smith', u'USER', u'A'),
   (u'BlueHeron', u'john.smith', u'DATA_LDS', u'A'),
   (u'BlueHeron', u'john.smith', u'DATA_OBFSC', u'A'),
   (u'BlueHeron', u'john.smith', u'DATA_AGG', u'A')]

'''

import injector
from injector import inject, provides, singleton
from sqlalchemy import Column, ForeignKey
from sqlalchemy import func
from sqlalchemy.orm import relationship
from sqlalchemy.orm.session import Session
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.types import String, Date, Enum
import sqlalchemy

import rtconfig
from orm_base import Base

CONFIG_SECTION='i2b2pm'


class I2B2PM(object):
    @inject(datasrc=(Session, CONFIG_SECTION))
    def __init__(self, datasrc):
        '''
        @param datasrc: a function that returns a sqlalchemy session
        '''
        self._datasrc = datasrc

    def ensure_account(self, uid,
                       project_id='BlueHeron',
                       roles = ('USER', 'DATA_LDS', 'DATA_OBFSC', 'DATA_AGG')):
        '''Ensure that an i2b2 account is ready for an authorized user.
        '''
        ds = self._datasrc()
        t = func.now()

        #import pdb
        #pdb.set_trace()

        # TODO: consider factoring out the "update the change_date
        # whenever you set a field" aspect of Audited.
        try:
            me = ds.query(User).filter(User.user_id==uid).one()
            if me.status_cd != 'A':
                me.status_cd, me.change_date = 'A', t
        except NoResultFound:
            me = User(user_id=uid,
                      entry_date=t, change_date=t, status_cd='A')
            ds.add(me)

        my_role_codes = [mr.user_role_cd for mr in me.roles]
        if [r for r in roles if not r in my_role_codes]:
            me.roles = [
                UserRole(user_id=uid, project_id=project_id,
                         user_role_cd=c,
                         entry_date=t, change_date=t, status_cd='A')
                for c in roles]

        ds.commit()



class Audited(object):
    change_date = Column(Date)
    entry_date = Column(Date)
    changeby_char = Column(String)  # foreign key?
    status_cd = Column(Enum('A', 'D'))


class User(Base, Audited):
    __tablename__ = 'pm_user_data'

    user_id = Column(String, primary_key=True)
    full_name = Column(String)
    password = Column(String)  # encrypted?
    email = Column(String)
    roles = relationship('UserRole', backref='pm_user_data')

    def ini(self, user_id,
                 full_name=None, password=None, email=None,
                 change_date=None, entry_date=None, changeby_char=None,
                 status_cd='A'):
        self.user_id = user_id
        self.full_name = full_name
        self.password = password
        self.email = email
        self._audit(change_date, entry_date,
                    changeby_char, status_cd='A')

    def __repr__(self):
        return "<User(%s)>" % self.user_id


class UserRole(Base, Audited):
    __tablename__ = 'pm_project_user_roles'

    project_id = Column(String, primary_key=True)  # ForeignKey?
    user_id = Column(String, 
                     ForeignKey('pm_user_data.user_id'),
                     primary_key=True)
    user_role_cd = Column(Enum('ADMIN', 'MANAGER', 'USER',
                               'DATA_OBFSC', 'DATA_AGG', 'DATA_DEID',
                               'DATA_LDS', 'DATA_PROT'),
                          primary_key=True)

    def __repr__(self):
        return "<UserRule(%s, %s, %s)>" % (self.project_id,
                                           self.user_id,
                                           self.user_role_cd)


class RunTime(rtconfig.IniModule):
    @provides((rtconfig.Options, CONFIG_SECTION))
    def settings(self):
        rt = rtconfig.RuntimeOptions(['url'])
        rt.load(self._ini, CONFIG_SECTION)
        return rt

    # abusing Session a bit; this really provides a subclass, not an instance, of Session
    @singleton
    @provides((sqlalchemy.orm.session.Session, CONFIG_SECTION))
    @inject(rt=(rtconfig.Options, CONFIG_SECTION))
    def pm_sessionmaker(self, rt):
        engine = sqlalchemy.engine_from_config(rt.settings(), 'sqlalchemy.')
        return sessionmaker(engine)


class Mock(injector.Module, rtconfig.MockMixin):
    '''Mock up I2B2PM dependencies: SQLite datasource
    '''
    @singleton
    @provides((sqlalchemy.orm.session.Session, CONFIG_SECTION))
    def pm_sessionmaker(self):
        engine = sqlalchemy.create_engine('sqlite://')
        Base.metadata.create_all(engine)
        return sessionmaker(engine)


def _test_main():
    import sys
    import logging

    logging.basicConfig(level=logging.DEBUG)
    salog = logging.getLogger('sqlalchemy.engine.base.Engine')
    salog.setLevel(logging.INFO)

    if '--list' in sys.argv:
        _list_users()
        return

    user_id = sys.argv[1]

    (pm, ) = RunTime.make(None, [I2B2PM])

    pm.ensure_account(user_id)


def _list_users():
    import csv, sys
    (sm, ) = RunTime.make(None,
                          [(sqlalchemy.orm.session.Session, CONFIG_SECTION)])
    s = sm()
    # get column names
    #ans = s.execute("select * from pm_user_session "
    #                "  where rownum < 2")
    #print ans.fetchone().items()

    ans = s.execute("select max(entry_date), count(*), user_id "
                    "  from pm_user_session "
                    "  where user_id not in ('OBFSC_SERVICE_ACCOUNT')"
                    "  group by user_id"
                    "  order by user_id")

    out = csv.writer(sys.stdout)
    out.writerow(('last_login', 'login_count', 'user_id'))
    out.writerows([(when.isoformat(), qty, uid)
                   for when, qty, uid in ans.fetchall()])


if __name__ == '__main__':
    _test_main()

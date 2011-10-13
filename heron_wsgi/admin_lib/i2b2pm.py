'''i2b2pm.py -- I2B2 Project Management cell client/proxy


Ensure account sets up the DB as the I2B2 project manager expects::

  >>> pm, depgraph = Mock.make_stuff()
  >>> pm.ensure_account('john.smith')

  >>> import pprint
  >>> dbsrc = depgraph.get((Session, __name__))
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
from injector import inject
from sqlalchemy import Column, ForeignKey, Unicode
from sqlalchemy import func
from sqlalchemy.ext.declarative import declarative_base, DeclarativeMeta
from sqlalchemy.orm import relationship
from sqlalchemy.orm.session import Session
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.types import String, Integer, Date, Enum
import sqlalchemy

import medcenter
import config


class I2B2PM(object):
    @inject(datasrc=(Session, __name__))
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

        # Is explicit flushing really the way the ORM is designed?
        ds.flush()



Base = declarative_base()

class Audited(object):
    change_date = Column(Date)
    entry_date = Column(Date)
    changeby_char = Column(String)  # foreign key?
    status_cd = Column(Enum('A', 'D'))


class User(Base, Audited):
#class User(Base):
    __tablename__ = 'pm_user_data'  #'PM_USER_DATA'
    #__table_args__ = {'schema':'i2b2pm'}

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


CONFIG_SECTION='i2b2pm'

class IntegrationTest(injector.Module):
    def __init__(self, ini='integration-test.ini'):
        injector.Module.__init__(self)
        self._ini = ini

    def configure(self, binder):
        binder.bind(DeclarativeMeta, Base)

        rt = config.RuntimeOptions(['url'])
        rt.load(self._ini, CONFIG_SECTION)
        settings = rt._d  # KLUDGE!
        engine = sqlalchemy.engine_from_config(settings, 'sqlalchemy.')
        Base.metadata.bind = engine
        binder.bind((Session, __name__),
                    injector.InstanceProvider(sessionmaker(engine)))

    @classmethod
    def mods(cls):
        return [cls()]

    @classmethod
    def depgraph(cls, ini='integration-test.ini'):
        return injector.Injector([class_(ini) for class_ in cls.deps()])


class Mock(injector.Module):
    '''Mock up I2B2PM dependencies: SQLite datasource
    '''
    def configure(self, binder):
        binder.bind(DeclarativeMeta, Base)

        engine = sqlalchemy.create_engine('sqlite://')
        Base.metadata.bind = engine
        Base.metadata.create_all(engine)
        binder.bind((Session, __name__),
                    injector.InstanceProvider(sessionmaker(engine)))

    @classmethod
    def mods(cls):
        return [cls()]

    @classmethod
    def make_stuff(cls, mods=None):
        if mods is None:
            mods = cls.mods()
        depgraph = injector.Injector(mods)
        return depgraph.get(I2B2PM), depgraph


if __name__ == '__main__':
    import sys
    user_id = sys.argv[1]

    depgraph = IntegrationTest.depgraph()
    mc = depgraph.get(medcenter.MedCenter)
    hr = depgraph.get(heron_policy.HeronRecords)
    pm = depgraph.get(I2B2PM)

    user_login_ok = hr.q_any(mc.affiliate(user_id))
    user_access = hr.repositoryAccess(user_login_ok)
    pm.ensure_account(user_access)

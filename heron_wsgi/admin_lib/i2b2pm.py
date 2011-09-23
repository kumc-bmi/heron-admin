'''i2b2pm.py -- I2B2 Project Management cell client/proxy

To create an I2B2PM proxy/client object, first we need a datasource,
i.e. a "session maker", connected to the "delcarative base" of our
model of i2b2 users and roles::

  >>> engine = sqlalchemy.create_engine('sqlite://')
  >>> Base.metadata.bind = engine
  >>> Base.metadata.create_all(engine)
  >>> dbsrc = sessionmaker(engine)

.. todo:: get rid of globals using injector

.. todo:: cite sqlalchemy docs for session maker, declarative base

Next, we'll need a heron_policy.HeronRecords checker:

  >>> mc = medcenter._mock()
  >>> hp = heron_policy._mock(mc)

Its audit method is the only part that the pm proxy actually uses::

  >>> pm = I2B2PM(dbsrc, heron_policy.audit)

Now, suppose we go through our HeronRecords to get an access token for
John Smith::

  >>> mc = medcenter._mock()
  >>> hp = heron_policy._mock(mc)
  >>> okjs = hp.q_any(mc.affiliate('john.smith'))

Then calling the ensure_account method should ensure the following
contents of the project management store::

  >>> pm.ensure_account(okjs)

  >>> import pprint
  >>> ans = dbsrc().execute('select project_id, user_id, '
  ...                       ' user_role_cd, status_cd'
  ...                       ' from pm_project_user_roles')
  >>> pprint.pprint(ans.fetchall())
  [(u'BlueHeron', u'john.smith', u'USER', u'A'),
   (u'BlueHeron', u'john.smith', u'DATA_LDS', u'A'),
   (u'BlueHeron', u'john.smith', u'DATA_OBFSC', u'A'),
   (u'BlueHeron', u'john.smith', u'DATA_AGG', u'A')]

'''

from sqlalchemy import Column, ForeignKey, Unicode
from sqlalchemy import func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.types import String, Integer, Date, Enum
import sqlalchemy

import heron_policy  # hmm... only for testing?
import medcenter
import config


class I2B2PM(object):
    def __init__(self, datasrc, audit):
        '''
        @param datasrc: a function that returns a sqlalchemy.Session
        @param audit: a function that audits an access capability
                      and returns a user id or raises and exception.
        '''
        self._datasrc = datasrc
        self._audit = audit

    def ensure_account(self, access,
                       project_id='BlueHeron',
                       roles = ('USER', 'DATA_LDS', 'DATA_OBFSC', 'DATA_AGG')):
        '''Ensure that an i2b2 account is ready for an authorized user.
        '''
        uid = self._audit(access)

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


def _integration_test(hp, ini='integration-test.ini'):
    '''
    '''
    rt = config.RuntimeOptions(['url'])
    rt.load(ini, 'i2b2pm')
    settings = rt._d  # KLUDGE!

    engine = sqlalchemy.engine_from_config(settings, 'sqlalchemy.')
    Base.metadata.bind = engine
    dbsrc = sessionmaker(engine)

    return I2B2PM(dbsrc, hp.audit)


if __name__ == '__main__':
    import sys
    user_id = sys.argv[1]

    mc = medcenter._integration_test()
    hp = heron_policy._integration_test(mc)
    pm = _integration_test(hp)

    user_login_ok = hp.q_any(mc.affiliate(user_id))
    pm.ensure_account(user_login_ok)
'''i2b2pm -- I2B2 Project Management accounts and permissions
-------------------------------------------------------------

We use :class:`I2B2PM` to manage user accounts and permissions in the
I2B2 project management cell via its database.

  >>> pm, dbsrc = Mock.make([I2B2PM, (orm.session.Session, CONFIG_SECTION)])

An object with a reference to this :class:`I2B2PM` can have us
generate authorization to access I2B2, once it has verified to its
satisfaction that the repository access policies are met.

For example, an object of the `I2B2Account` nested class of
:mod:`heron_wsgi.admin_lib.heron_policy.HeronRecords` would generate a
one-time authorization password and the corresponding hashed form for
John Smith like this::

  >>> pw, js = pm.authz('john.smith', 'John Smith')
  >>> pw
  'dfd03595-ab3e-4448-9c8e-a65a290cc3c5'

The password field in the `User` record is hashed::

  >>> js.password
  u'da67296336429545fe63f61644e420'

The effect is a `pm_user_data` record::

  >>> import pprint
  >>> ans = dbsrc().execute('select user_id, password, status_cd'
  ...                       ' from pm_user_data')
  >>> pprint.pprint(ans.fetchall())
  [(u'john.smith', u'da67296336429545fe63f61644e420', u'A')]

... and appropriate `pm_project_user_roles` records::

  >>> ans = dbsrc().execute('select project_id, user_id, '
  ...                       ' user_role_cd, status_cd'
  ...                       ' from pm_project_user_roles')
  >>> pprint.pprint(ans.fetchall())
  [(u'BlueHeron', u'john.smith', u'USER', u'A'),
   (u'BlueHeron', u'john.smith', u'DATA_LDS', u'A'),
   (u'BlueHeron', u'john.smith', u'DATA_OBFSC', u'A'),
   (u'BlueHeron', u'john.smith', u'DATA_AGG', u'A')]

If John logs in again, a new one-time authorization is issued::

  >>> auth, js2 = pm.authz('john.smith', 'John Smith')
  >>> auth
  '89cd1d9a-ace1-4673-8a12-50ebac2625f9'

This updates the `password` column of the `pm_user_data` record::

  >>> ans = dbsrc().execute('select user_id, password, status_cd'
  ...                       ' from pm_user_data')
  >>> pprint.pprint(ans.fetchall())
  [(u'john.smith', u'e5ab367ceece604b7f7583d024ac4e2b', u'A')]

'''

import logging
import uuid
import hashlib

import injector
from injector import inject, provides, singleton
from sqlalchemy import Column, ForeignKey
from sqlalchemy import func, orm
from sqlalchemy.types import String, Date, Enum
from sqlalchemy.ext.declarative import declarative_base
import sqlalchemy

import rtconfig
import jndi_util
import ocap_file

CONFIG_SECTION = 'i2b2pm'
KUUIDGen = injector.Key('UUIDGen')

Base = declarative_base()
log = logging.getLogger(__name__)


class I2B2PM(object):
    @inject(datasrc=(orm.session.Session, CONFIG_SECTION),
            uuidgen=KUUIDGen)
    def __init__(self, datasrc, uuidgen):
        '''
        :param datasrc: a function that returns a sqlalchemy session
        '''
        self._datasrc = datasrc
        self._uuidgen = uuidgen

    def authz(self, uid, full_name,
              project_id='BlueHeron',
              roles=('USER', 'DATA_LDS', 'DATA_OBFSC', 'DATA_AGG')):
        '''Generate authorization to use an i2b2 project.
        '''
        log.debug('generate authorization for: %s', (uid, full_name))
        ds = self._datasrc()
        t = func.now()
        auth = str(self._uuidgen.uuid4())
        pw = hexdigest(auth)

        # TODO: consider factoring out the "update the change_date
        # whenever you set a field" aspect of Audited.
        try:
            me = ds.query(User).filter(User.user_id == uid).one()
            me.password, me.status_cd, me.change_date = pw, 'A', t
            log.info('found: %s', me)
        except orm.exc.NoResultFound:
            me = User(user_id=uid, full_name=full_name,
                      entry_date=t, change_date=t, status_cd='A',
                      password=pw,
                      roles=ds.query(UserRole).filter_by(user_id=uid).all())
            log.info('adding: %s', me)
            ds.add(me)

        my_role_codes = [mr.user_role_cd for mr in me.roles
                         if mr.project_id == project_id]
        log.debug('my role codes: %s', my_role_codes)
        for r in roles:
            if r not in my_role_codes:
                myrole = UserRole(user_id=uid, project_id=project_id,
                                  user_role_cd=r,
                                  entry_date=t, change_date=t, status_cd='A')
                log.info('I2B2PM: adding: %s', myrole)
                me.roles.append(myrole)

        ds.commit()
        return auth, me


def hexdigest(txt):
    '''mimic i2b2's own hex digest algorithm

    It seems to omit leading 0's.

    >>> hexdigest('test')
    '98f6bcd4621d373cade4e832627b4f6'
    '''
    return ''.join([hex(ord(b))[2:] for b in hashlib.md5(txt).digest()])


def revoke_expired_auths(ds):
    '''Revoke one-time passwords for all users whose sessions are expired.
    '''
    ds.execute('''
    update i2b2pm.pm_user_data ipud
    set ipud.password = null
    where
        ipud.user_id not like '%SERVICE_ACCOUNT'
        and ipud.password is not null and (
        select max(ipus.expired_date)
        from i2b2pm.pm_user_session ipus
        where ipus.user_id = ipud.user_id) < sysdate
    ''')
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
    password = Column(String)  # hex(md5sum(password))
    email = Column(String)
    roles = orm.relationship('UserRole', backref='pm_user_data')

    def __repr__(self):
        return "<User(%s, %s)>" % (self.user_id, self.full_name)


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
        rt = rtconfig.RuntimeOptions(['jboss_deploy'])
        rt.load(self._ini, CONFIG_SECTION)
        return rt

    @singleton
    @provides(jndi_util.JBossContext)
    @inject(rt=(rtconfig.Options, CONFIG_SECTION))
    def jndi_context(self, rt):
        import os  # hmm... where to import?
        jd = ocap_file.Readable(rt.jboss_deploy, os.path, os.listdir, open)
        return jndi_util.JBossContext(jd, sqlalchemy.create_engine)

    jndi_name = 'PMBootStrapDS'

    # abusing Session a bit; this really provides a subclass, not an
    # instance, of Session
    @singleton
    @provides((orm.session.Session, CONFIG_SECTION))
    @inject(ctx=jndi_util.JBossContext)
    def pm_sessionmaker(self, ctx):
        engine = ctx.lookup(self.jndi_name)
        sm = orm.session.sessionmaker(engine)

        def make_session_and_revoke():
            ds = sm()
            revoke_expired_auths(ds)
            return ds

        return make_session_and_revoke

    @provides(KUUIDGen)
    def uuid_maker(self):
        return uuid


class Mock(injector.Module, rtconfig.MockMixin):
    '''Mock up I2B2PM dependencies: SQLite datasource
    '''
    @singleton
    @provides((orm.session.Session, CONFIG_SECTION))
    def pm_sessionmaker(self):
        engine = sqlalchemy.create_engine('sqlite://')
        Base.metadata.create_all(engine)
        return orm.session.sessionmaker(engine)

    @provides(KUUIDGen)
    def uuid_maker(self):
        class G(object):
            def __init__(self):
                from uuid import UUID
                self._d = iter([UUID('dfd03595-ab3e-4448-9c8e-a65a290cc3c5'),
                                UUID('89cd1d9a-ace1-4673-8a12-50ebac2625f9'),
                                UUID('dc584070-9e36-493e-80ce-ac277c1ce611'),
                                UUID('0100f48b-c313-4086-92a9-6bfc621cc0df'),
                                UUID('537d9d95-b017-4d9d-b096-2d1af316eb86')])

            def uuid4(self):
                return self._d.next()

        return G()


def _test_main():
    import sys

    logging.basicConfig(level=logging.DEBUG)
    salog = logging.getLogger('sqlalchemy.engine.base.Engine')
    salog.setLevel(logging.INFO)

    if '--list' in sys.argv:
        _list_users()
        return

    user_id, full_name = sys.argv[1:3]

    (pm, ) = RunTime.make(None, [I2B2PM])

    print pm.authz(user_id, full_name)


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

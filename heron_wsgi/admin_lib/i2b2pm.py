'''i2b2pm -- I2B2 Project Management accounts and permissions
-------------------------------------------------------------

We use :class:`I2B2PM` to manage user accounts and permissions in the
I2B2 project management cell via its database.

  >>> pm, dbsrc, rcsm, mdsm, rcp = Mock.make([I2B2PM, (orm.session.Session,
  ...     CONFIG_SECTION), (orm.session.Session, redcapdb.CONFIG_SECTION),
  ...    (orm.session.Session, CONFIG_SECTION_MD),
  ...    redcap_projects.REDCap_projects])

An object with a reference to this :class:`I2B2PM` can have us
generate authorization to access I2B2, once it has verified to its
satisfaction that the repository access policies are met.

For example, an object of the `I2B2Account` nested class of
:mod:`heron_wsgi.admin_lib.heron_policy.HeronRecords` would generate a
one-time authorization password and the corresponding hashed form for
John Smith like this::

  >>> pw, js = pm.authz('john.smith', 'John Smith')
  BlueHeron
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
  BlueHeron
  >>> auth
  '89cd1d9a-ace1-4673-8a12-50ebac2625f9'

This updates the `password` column of the `pm_user_data` record::

  >>> ans = dbsrc().execute('select user_id, password, status_cd'
  ...                       ' from pm_user_data')
  >>> pprint.pprint(ans.fetchall())
  [(u'john.smith', u'e5ab367ceece604b7f7583d024ac4e2b', u'A')]

Now giving user john.smith permissions to redcap projects

  >>> _mock_redcap_permissions(pm._rcsm(), 'john.smith')

Making up 4 i2b2 projects
The first project should be selected
  >>> _mock_i2b2_projects(dbsrc(), 1, ['0', '0', '0', '0'])
  >>> pw, js = pm.authz('john.smith', 'John Smith')
  REDCap_1

Creating roles for the user for some projects
An empty project should be selected
  >>> _mock_i2b2_roles(dbsrc(), ['1', '2', '3'])
  >>> pw, js = pm.authz('john.smith', 'John Smith')
  REDCap_4

Creating a project that has the exact data
The project with exact data should be selected
  >>> _mock_i2b2_projects(dbsrc(), 5, ['redcap_1_11_91'])
  >>> pw, js = pm.authz('john.smith', 'John Smith')
  REDCap_5

Creating roles for the users for all projects so they are no empty projects
Should fall back to the last picked project instead of blueheron
  >>> _mock_i2b2_roles(dbsrc(), ['4', '5'])
  >>> pw, js = pm.authz('john.smith', 'John Smith')
  REDCap_5

  Next tests
  _mock_i2b2_usage(dbsrc())
  pw, js = pm.authz('john.smith', 'John Smith')

'''

import logging
import uuid  # @@code review: push into TCB
import hashlib
from datetime import date

import injector
from injector import inject, provides, singleton
from sqlalchemy import Column, ForeignKey
from sqlalchemy import func, orm
from sqlalchemy.types import String, Date, Enum, Integer
from sqlalchemy.ext.declarative import declarative_base

import rtconfig
import jndi_util
import ocap_file
import redcapdb
import redcap_projects

CONFIG_SECTION = 'i2b2pm'
CONFIG_SECTION_MD = 'i2b2md'

KUUIDGen = injector.Key('UUIDGen')

Base = declarative_base()
log = logging.getLogger(__name__)


class I2B2PM(ocap_file.Token):
    @inject(datasrc=(orm.session.Session, CONFIG_SECTION),
            redcap_sessionmaker=(orm.session.Session,
                                 redcapdb.CONFIG_SECTION),
            rcp=redcap_projects.REDCap_projects,
            metadatasm=(orm.session.Session,
                                 CONFIG_SECTION_MD),
            uuidgen=KUUIDGen)
    def __init__(self, datasrc, redcap_sessionmaker, metadatasm, uuidgen, rcp):
        '''
        :param datasrc: a function that returns a sqlalchemy session
        '''
        self._datasrc = datasrc
        self._rcsm = redcap_sessionmaker
        self._mdsm = metadatasm
        self._uuidgen = uuidgen
        self._rcp = rcp

    def account_for(self, agent):
        return I2B2Account(self, agent)

    def authz(self, uid, full_name,
              project_id='BlueHeron',
              roles=('USER', 'DATA_LDS', 'DATA_OBFSC', 'DATA_AGG')):
        '''Generate authorization to use an i2b2 project.
        '''
        log.debug('generate authorization for: %s', (uid, full_name))
        ds = self._datasrc()
        rs = self._rcsm()
        t = func.now()
        auth = str(self._uuidgen.uuid4())
        pw = hexdigest(auth)
        rc_user_projs = rs.query(RedcapUser).filter(
                        RedcapUser.username == uid).all()

        #Does user have permissions to REDCap projects?
        rc_pids = [row.project_id
                   for row in rc_user_projs]
        if rc_pids:
            project_id_rc = self._rcp.pick_project(uid, rc_pids, ds,
                            self._mdsm(), Project, UserRole, UserSession)
            if project_id_rc:
                project_id = project_id_rc

        print project_id
        # TODO: consider factoring out the "update the change_date
        # whenever you set a field" aspect of Audited.
        try:
            #Check if the user already exists in pm_user_roles
            # TODO: ***change the following to check project also***
            me = ds.query(User).filter(User.user_id == uid).one()
            me.password, me.status_cd, me.change_date = pw, 'A', t
            log.info('found: %s', me)
        except orm.exc.NoResultFound:
            #If the user doesn't exist in pm_user_roles, add him
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


class I2B2Account(ocap_file.Token):
    def __init__(self, pm, agent):
        self.__pm = pm
        self.__agent = agent

    def __repr__(self):
        return 'Access(%s)' % self.__agent

    def creds(self):
        agent = self.__agent
        key, u = self.__pm.authz(agent.cn, agent.full_name())
        return (agent.cn, key)


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

    project_id = Column(String, ForeignKey('pm_project_data.project_id'),
                        primary_key=True)
    user_id = Column(String,
                     ForeignKey('pm_user_data.user_id'),
                     primary_key=True)
    user_role_cd = Column(Enum('ADMIN', 'MANAGER', 'USER',
                               'DATA_OBFSC', 'DATA_AGG', 'DATA_DEID',
                               'DATA_LDS', 'DATA_PROT'),
                          primary_key=True)

    def __repr__(self):
        return "<UserRole(%s, %s, %s)>" % (self.project_id,
                                           self.user_id,
                                           self.user_role_cd)


class UserSession(Base, Audited):
    __tablename__ = 'pm_user_session'

    user_id = Column(String,
                     ForeignKey('pm_user_data.user_id'),
                     primary_key=True)
    expired_date = Column(Date)

    def __repr__(self):
        return "<UserSession(%s, %s)>" % (self.user_id,
                                           self.expired_date)


class Project(Base, Audited):
    __tablename__ = 'pm_project_data'

    project_id = Column(String, primary_key=True)
    project_description = Column(String)

    def __repr__(self):
        return "<Project(%s, %s)>" % (self.project_id,
                                           self.project_description)


class RedcapUser(Base, Audited):
    __tablename__ = 'redcap_user_rights'

    project_id = Column(Integer, primary_key=True)
    username = Column(String, primary_key=True)

    def __repr__(self):
        return "<RedcapUser(%s, %s)>" % (self.project_id,
                                           self.username)


class RunTime(rtconfig.IniModule):  # pragma: nocover
    jndi_name = 'PMBootStrapDS'
    jndi_name_md = 'REDCapMDDS'

    # abusing Session a bit; this really provides a subclass, not an
    # instance, of Session
    def sessionmaker(self, jndi, CONFIG):
        import os
        from sqlalchemy import create_engine

        rt = rtconfig.RuntimeOptions(['jboss_deploy'])
        rt.load(self._ini, CONFIG)

        jdir = ocap_file.Readable(rt.jboss_deploy, os.path, os.listdir, open)
        ctx = jndi_util.JBossContext(jdir, create_engine)

        sm = orm.session.sessionmaker()

        def make_session_and_revoke():
            engine = ctx.lookup(jndi)
            ds = sm(bind=engine)
            revoke_expired_auths(ds)
            return ds

        return make_session_and_revoke

    @singleton
    @provides((orm.session.Session, CONFIG_SECTION))
    def pm_sessionmaker(self):
        return self.sessionmaker(self.jndi_name, CONFIG_SECTION)

    @singleton
    @provides((orm.session.Session, CONFIG_SECTION_MD))
    def md_sessionmaker(self):
        return self.sessionmaker(self.jndi_name_md, CONFIG_SECTION_MD)

    @provides(KUUIDGen)
    def uuid_maker(self):
        return uuid


class Mock(injector.Module, rtconfig.MockMixin):
    '''Mock up I2B2PM dependencies: SQLite datasource
    '''
    @singleton
    @provides((orm.session.Session, CONFIG_SECTION))
    def pm_sessionmaker(self):
        from sqlalchemy import create_engine

        engine = create_engine('sqlite://')
        Base.metadata.create_all(engine)
        return orm.session.sessionmaker(engine)

    @provides((orm.session.Session, redcapdb.CONFIG_SECTION))
    def rc_sessionmaker(self):
        from sqlalchemy import create_engine

        engine = create_engine('sqlite://')
        Base.metadata.create_all(engine)
        return orm.session.sessionmaker(engine)

    @provides((orm.session.Session, CONFIG_SECTION_MD))
    def mdsm_sessionmaker(self):
        from sqlalchemy import create_engine

        engine = create_engine('sqlite://')
        Base.metadata.create_all(engine)
        return orm.session.sessionmaker(engine)

    @provides(redcap_projects.REDCap_projects)
    def redcap_projectmaker(self):
        return redcap_projects.REDCap_projects()

    @provides(KUUIDGen)
    def uuid_maker(self):
        class G(object):
            def __init__(self):
                from uuid import UUID
                self._d = iter([UUID('dfd03595-ab3e-4448-9c8e-a65a290cc3c5'),
                                UUID('89cd1d9a-ace1-4673-8a12-50ebac2625f9'),
                                UUID('dc584070-9e36-493e-80ce-ac277c1ce611'),
                                UUID('0100f48b-c313-4086-92a9-6bfc621cc0df'),
                                UUID('537d9d95-b017-4d9d-b096-2d1af316eb86'),
                                UUID('537d9d95-b017-4d9d-b096-2d1af316eb34'),
                                UUID('537d9d95-b017-4d9d-b096-2d1af316eb92')])

            def uuid4(self):
                return self._d.next()

        return G()


def _mock_redcap_permissions(rcsm, uid):
    '''Mock up user permissions to redcap projects
    '''
    rcsm.add_all([RedcapUser(project_id=01, username=uid),
                  RedcapUser(project_id=91, username=uid),
                  RedcapUser(project_id=11, username=uid)])
    rcsm.commit()


def _mock_i2b2_projects(ds, i, proj_desc):
    '''Mock up i2b2 projects
    '''
    for desc in proj_desc:
        if desc == '0':
            desc = ''
        ds.add(Project(project_id='REDCap_' + str(i),
                       project_description=desc))
        i += 1
    ds.commit()


def _mock_i2b2_usage(ds):
    '''Mock up user permissions to redcap projects
    '''
    ds.add_all([UserSession(user_id='john.smith',
                            expired_date=date(2013, 3, 1)),
                UserSession(user_id='barn.smith',
                            expired_date=date(2013, 4, 8)),
                UserSession(user_id='kyon.smith',
                            expired_date=date(2013, 4, 1))
                ])
    ds.commit()


def _mock_i2b2_roles(ds, pids):
    '''Mock up user permissions to i2b2 projects
    '''
    i = 1
    for pid in pids:
        ds.add(UserRole(user_id='john.smith' + str(i),
                        project_id='REDCap_' + pid,
                        user_role_cd='DATA_LDS'))
        ds.commit()


def _integration_test():  # pragma: nocover
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


def _list_users():  # pragma: nocover
    import csv, sys
    (sm, ) = RunTime.make(None,
                          [(orm.session.Session, CONFIG_SECTION)])
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


if __name__ == '__main__':  # pragma: nocover
    _integration_test()

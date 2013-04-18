'''i2b2pm -- I2B2 Project Management accounts and permissions
-------------------------------------------------------------

We use :class:`I2B2PM` to manage user accounts and permissions in the
I2B2 project management cell via its database.

  >>> pm, dbsrc, md = Mock.make([I2B2PM, (orm.session.Session,
  ...     CONFIG_SECTION), i2b2metadata.I2B2Metadata])

An object with a reference to this :class:`I2B2PM` can have us
generate authorization to access I2B2, once it has verified to its
satisfaction that the repository access policies are met.

For example, an object of the `I2B2Account` nested class of
:mod:`heron_wsgi.admin_lib.heron_policy.HeronRecords` would generate a
one-time authorization password and the corresponding hashed form for
John Smith like this::

  >>> pw, js = pm.authz('john.smith', 'John Smith', 'BlueHeron')
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

  >>> auth, js2 = pm.authz('john.smith', 'John Smith', 'BlueHeron')
  >>> auth
  '89cd1d9a-ace1-4673-8a12-50ebac2625f9'

This updates the `password` column of the `pm_user_data` record::

  >>> ans = dbsrc().execute('select user_id, password, status_cd'
  ...                       ' from pm_user_data')
  >>> pprint.pprint(ans.fetchall())
  [(u'john.smith', u'e5ab367ceece604b7f7583d024ac4e2b', u'A')]

= REDCap Projects =

When john.smith has permissions to no redcap data he is directed to blueheron
  >>> pm1, dbsrc1, md1 = Mock.make([I2B2PM, (orm.session.Session,
  ...     CONFIG_SECTION), i2b2metadata.I2B2Metadata])
  >>> pm1.i2b2_project([])
  'BlueHeron'

john.smith has permissions to 3 redcap projects with pids 1, 11, 91
Mocking up i2b2 redcap projects REDCap_1, REDCap_2...
All the projects have NULL project_description
When john.smith logs in, he is directed to the first project
  >>> pm2, dbsrc2, md2 = Mock.make([I2B2PM, (orm.session.Session,
  ...     CONFIG_SECTION), i2b2metadata.I2B2Metadata])
  >>> _mock_i2b2_projects(dbsrc2(), 1, ['0', '0', '0', '0'])
  >>> pm2.i2b2_project([1, 11, 91])
  u'REDCap_1'

john.smith has permissions to 3 redcap projects with pids 1, 11, 91
Mocking up some user roles for i2b2 projects
When john.smith logs in, he is directed to the project with no users attached
  >>> pm3, dbsrc3, md3  = Mock.make([I2B2PM, (orm.session.Session,
  ...     CONFIG_SECTION), i2b2metadata.I2B2Metadata])
  >>> _mock_i2b2_projects(dbsrc3(), 1, ['0', '0', '0', '0'])
  >>> _mock_i2b2_roles(dbsrc3(), ['1', '2', '3'])
  >>> pm3.i2b2_project([1, 11, 91])
  u'REDCap_4'

john.smith has permissions to 3 redcap projects with pids 1, 11, 91
But data from on pids 1, 91 is in HERON
Mocking up an i2b2 project (REDCap_5) which has data from REDCap pids 1,91
When john.smith logs in he is directed to REDCap_5
  >>> pm4, dbsrc4, md4 = Mock.make([I2B2PM, (orm.session.Session,
  ...     CONFIG_SECTION), i2b2metadata.I2B2Metadata])
  >>> _mock_i2b2_projects(dbsrc4(), 1, ['0', '0', '0', '0'])
  >>> _mock_i2b2_roles(dbsrc4(), ['1', '2', '3'])
  >>> _mock_i2b2_projects(dbsrc4(), 5, ['redcap_1_91'])
  >>> pm4.i2b2_project([1, 11, 91])
  u'REDCap_5'

john.smith has permissions to 3 redcap projects with pids 1, 11, 91
Mocking up some user roles for all available i2b2 projects so none is available
When john.smith logs in he is directed to Blueheron
  >>> pm5, dbsrc5, md5 = Mock.make([I2B2PM, (orm.session.Session,
  ...     CONFIG_SECTION), i2b2metadata.I2B2Metadata])
  >>> _mock_i2b2_projects(dbsrc5(), 1, ['0', '0', '0', '0'])
  >>> _mock_i2b2_roles(dbsrc5(), ['1', '2', '3'])
  >>> _mock_i2b2_roles(dbsrc5(), ['4', '5'])
  >>> pm5.i2b2_project([1, 11, 91])
  'BlueHeron'

'''

import logging
import uuid  # @@code review: push into TCB
import hashlib
from datetime import date

import injector
from injector import inject, provides, singleton
from sqlalchemy import Column, ForeignKey
from sqlalchemy import func, orm
from sqlalchemy.types import String, Date, Enum
from sqlalchemy.ext.declarative import declarative_base

import rtconfig
import jndi_util
import ocap_file
import i2b2metadata

CONFIG_SECTION = 'i2b2pm'

KUUIDGen = injector.Key('UUIDGen')

Base = declarative_base()
log = logging.getLogger(__name__)


class I2B2PM(ocap_file.Token):
    @inject(datasrc=(orm.session.Session, CONFIG_SECTION),
            i2b2md=i2b2metadata.I2B2Metadata,
            uuidgen=KUUIDGen)
    def __init__(self, datasrc, i2b2md, uuidgen):
        '''
        :param datasrc: a function that returns a sqlalchemy session
        '''
        self._datasrc = datasrc
        self._md = i2b2md
        self._uuidgen = uuidgen

    def account_for(self, agent, rc_pids):
        return I2B2Account(self, agent, rc_pids)

    def i2b2_project(self, rc_pids, default_pid='BlueHeron'):
        '''select project based on redcap projects user has access to.
        '''
        pms = self._datasrc()
        log.debug('User has access to REDCap pids: %s', rc_pids)
        rc_pids = self._md.rc_in_i2b2(rc_pids)
        if not rc_pids:
            log.debug('User REDCap projects are not in HERON')
            return default_pid
        log.debug('REDCap pids that are in HERON: %s', rc_pids)

        proj_desc = 'redcap_' + ('_'.join([str(pid)
                                              for pid in sorted(rc_pids)]))
        log.debug('proj_desc in pick_project: %s', proj_desc)

        def ready_project():
            #is there already an existing project with this redcap data?
            rs = pms.query(Project).filter_by(
                    project_description=proj_desc).order_by(
                                        Project.project_id.desc()).first()
            log.debug('rs in pick_project: %s', rs)
            return rs

        def empty_project():
            #is there an empty redcap_i project available
            x = [rs.project_id for rs in pms.query(UserRole).all()]
            i2b2_pids = [rs.project_id for rs in pms.query(Project).\
                         filter(Project.project_id.like('REDCap_%')).all()]
            empty_pid_list = list(set(i2b2_pids).difference(set(x)))
            #set(x) will remove duplicates. So no need for distinct.
            return sorted(empty_pid_list)[0] if empty_pid_list else False

        def update_desc(pid, proj_desc):
            log.debug('Update description of project %s to %s',
                      pid, proj_desc)
            pms.query(Project).filter_by(
                    project_id=pid).update({"project_description": proj_desc})
            pms.commit()

        ready_pid = ready_project()
        empty_pid = empty_project()

        #A more elegant way to write this?
        if ready_pid:
            pid = ready_pid.project_id
            update_desc(pid, proj_desc)
            return pid
        elif empty_pid:
            self._md.project_terms(empty_pid, rc_pids)
            update_desc(empty_pid, proj_desc)
            return empty_pid
        else:
            return default_pid

    def authz(self, uid, full_name,
              project_id,
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
            #TODO: 1880 Is there a need to delete existing project roles here?
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
    def __init__(self, pm, agent, rc_pids):
        self.__pm = pm
        self.__agent = agent
        self._rc_pids = rc_pids

    def __repr__(self):
        return 'Access(%s)' % self.__agent

    def creds(self):
        agent = self.__agent
        project_id = self.__pm.i2b2_project(agent.cn, self.__rc_pids)
        key, u = self.__pm.authz(agent.cn, agent.full_name(), project_id)
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
    @provides(i2b2metadata.I2B2Metadata)
    @inject(mdsm=(orm.session.Session, i2b2metadata.CONFIG_SECTION_MD))
    def metadata(self, mdsm):
        imd = i2b2metadata.I2B2Metadata(mdsm)
        return imd

    @provides(KUUIDGen)
    def uuid_maker(self):
        return uuid

    @classmethod
    def mods(cls, ini):
        return [i2b2metadata.RunTime(ini), cls(ini)]


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

    @provides(i2b2metadata.I2B2Metadata)
    def metadata(self):
            return i2b2metadata.MockMetadata(1)

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
    #python i2b2pm.py badagarla 12,11,53 'Bhargav A'
    import sys

    logging.basicConfig(level=logging.DEBUG)
    salog = logging.getLogger('sqlalchemy.engine.base.Engine')
    salog.setLevel(logging.INFO)

    if '--list' in sys.argv:
        _list_users()
        return

    user_id, rc_pids, full_name = sys.argv[1:4]

    (pm, ) = RunTime.make(None, [I2B2PM])
    t = pm.i2b2_project(rc_pids.split(','))
    print "THE PROJECT THAT WAS PICKED: %s" % (t)
    print pm.authz(user_id, full_name, t)


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

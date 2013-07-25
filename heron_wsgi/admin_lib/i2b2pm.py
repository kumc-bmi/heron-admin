"""i2b2pm -- Just-in-time I2B2 Project accounts and permissions
---------------------------------------------------------------

We use :class:`I2B2PM` to establish user accounts and permissions in
the I2B2 project management cell that represent a HERON user's authority.

  >>> pm, storyparts = Mock.make([I2B2PM, None])

An object with a reference to this :class:`I2B2PM` can have us
generate authorization to access I2B2, once it has verified to its
satisfaction that the repository access policies are met.  For
example, to generate a one-time authorization password and the
corresponding hashed form for a qualified investigator who has signed
the system access agreement and acknowledged the disclaimer::

  >>> pw, js = pm.authz('john.smith', 'John Smith', 'BlueHeron')
  >>> pw
  'dfd03595-ab3e-4448-9c8e-a65a290cc3c5'

The password field in the `User` record is hashed::

  >>> js.password
  u'da67296336429545fe63f61644e420'


The effect is a `pm_user_data` record::

  >>> dbsrc = storyparts.get((orm.session.Session, CONFIG_SECTION))
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


Access to REDCap Data
=====================

When REDCap data is integrated into HERON, HERON users should have
access to the REDCap data corresponding to the REDCap projects that
they have access to. Access to REDCap data is controlled via metadata.
One I2B2 project can be shared among multiple HERON users that have
access to the same REDCap projects.

  >>> pm, md, dbsrc = Mock.make([
  ...     I2B2PM, i2b2metadata.I2B2Metadata,
  ...     (orm.session.Session, CONFIG_SECTION)])


Suppose redcap projects 1, 2, 3, and 4 have been loaded into HERON,
but their metadata has not been associated with any I2B2 projects:

  >>> _mock_i2b2_projects(dbsrc(),
  ...                     ((1, None), (2, None), (3, None), (4, None)))

The default HERON project has no REDCap data, so it is a suitable
project in the case where the list of REDCap projects is empty:

  >>> pm.i2b2_project([])
  ('BlueHeron', None)

Suppose a HERON user has permission to REDCap projects 1, 11, and 91.
Note that REDCap project 11 is not loaded into HERON.  The first
available I2B2 project is selected and its description and metadata
are updated suitably:

  >>> pm.i2b2_project([1, 11, 91])
  (u'REDCap_1', 'redcap_1_91')


In another case, suppose 4 i2b2 projects are created and eventually 1,
2, and 3 get associated REDCap metadata:

  >>> pm, md, dbsrc, storyparts = Mock.make([
  ...     I2B2PM, i2b2metadata.I2B2Metadata,
  ...     (orm.session.Session, CONFIG_SECTION), None])
  >>> _mock_i2b2_projects(dbsrc(),
  ...                     ((1, None), (2, None), (3, None), (4, None)))
  >>> _mock_i2b2_proj_usage(dbsrc(),
  ...                       (('1', 'redcap_10'),
  ...                        ('2', 'redcap_20'),
  ...                        ('3', 'redcap_30')))

Someone with permissions to REDCap projects 1, 11, and 91 is directed
to as-yet-unused I2B2 project:

  >>> pm.i2b2_project([1, 11, 91])
  (u'REDCap_4', 'redcap_1_91')

Another users with permissions to REDCap projects 1, 11, and 91
can use the same I2B2 project:

  >>> pm.i2b2_project([1, 11, 91])
  (u'REDCap_4', 'redcap_1_91')

At this point, all the I2B2 projects have associated REDCap metadata.
A user with access to an as-yet-unseen list of REDCap projects
is referred to the default project:

  >>> pm.i2b2_project([1, 41, 71])
  ('BlueHeron', None)


Suppose John Smith logs in to one HERON project; he'll be
given roles to that project & the default project - BlueHeron:

  >>> s = dbsrc()
  >>> auth, js3 = pm.authz('john.smith', 'John Smith', 'REDCap_1')
  >>> js = s.query(User).filter_by(user_id = 'john.smith').one()
  >>> set([role.project_id for role in js.roles])
  set([u'BlueHeron', u'REDCap_1'])

If his REDCap rights are changed, he'll get access to a different
I2B2 project; his roles in the above project go away:

  >>> s = dbsrc()
  >>> auth, js3 = pm.authz('john.smith', 'John Smith', 'REDCap_4')
  >>> js = s.query(User).filter_by(user_id = 'john.smith').one()
  >>> set([role.project_id for role in js.roles])
  set([u'REDCap_4', u'BlueHeron'])

If he has an ADMIN role when he logs in, the Admin role should not be deleted.
The ADMIN role is not project specific:
  >>> s = dbsrc()
  >>> admin_role = UserRole(user_id='john.smith', project_id='@',
  ...     user_role_cd='ADMIN', status_cd='A')
  >>> s.add(admin_role)
  >>> auth, js3 = pm.authz('john.smith', 'John Smith', 'REDCap_4')
  >>> js = s.query(User).filter_by(user_id = 'john.smith').one()
  >>> set([role.user_role_cd for role in js.roles])
  set(['ADMIN', u'DATA_OBFSC', u'USER', u'DATA_LDS', u'DATA_AGG'])
  >>> set([role.project_id for role in js.roles])
  set(['@', u'REDCap_4', u'BlueHeron'])

"""

import logging
import uuid  # @@code review: push into TCB
import hashlib

import injector
from injector import inject, provides, singleton
from sqlalchemy import Column, ForeignKey, and_
from sqlalchemy import func, orm
from sqlalchemy.types import String, Date, Enum
from sqlalchemy.ext.declarative import declarative_base

import rtconfig
import jndi_util
import ocap_file
import i2b2metadata

CONFIG_SECTION = 'i2b2pm'

KUUIDGen = injector.Key('UUIDGen')

DEFAULT_PID = 'BlueHeron'

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

    def account_for(self, agent, project_id):
        '''Build a facet with authority reduced to one user and one project.

        Note: We only use the agent cn and full_name(), not its
              unforgeable authority. The caller is responsible for
              policy enforcement.
        '''
        return I2B2Account(self, agent, project_id)

    def i2b2_project(self, rc_pids):
        '''select project based on redcap projects user has access to.

        :return: (project_id, project_desc)
        '''
        default_pid = DEFAULT_PID
        pms = self._datasrc()
        log.info('Finding I2B2 project for REDCap pids: %s', rc_pids)
        rc_pids = self._md.rc_in_i2b2(rc_pids)
        if not rc_pids:
            log.info('User REDCap projects are not in HERON')
            return default_pid, None
        log.debug('REDCap pids that are in HERON: %s', rc_pids)

        proj_desc = proj_desc_for(rc_pids)
        log.debug('proj_desc in pick_project: %s', proj_desc)

        def ready_project():
            '''Is there already an existing project with this redcap data?
            '''
            # Note first() returns None if there is no such project.
            rs = pms.query(Project).filter_by(
                    project_description=proj_desc).order_by(
                                        Project.project_id.desc()).first()
            log.debug('rs in pick_project: %s', rs)
            return rs

        def empty_project():
            '''Find a REDCap project whose project_description has
            not been set.
            '''
            return pms.query(Project).\
                        filter(Project.project_description == None).\
                        filter(Project.project_id.like('REDCap_%')).first()

        def update_desc(project, proj_desc):
            log.info('Update description of project %s to %s',
                      project.project_id, proj_desc)
            project.project_description = proj_desc
            pms.commit()
            return project.project_id, proj_desc

        ready = ready_project()
        if ready:
            return update_desc(ready, proj_desc)
        else:
            empty = empty_project()
            if empty:
                self._md.project_terms(empty.project_id, rc_pids)
                return update_desc(empty, proj_desc)

        log.warn('Ran out of projects! Using default.')
        return default_pid, None

    def authz(self, uid, full_name,
              project_id,
              roles=('USER', 'DATA_LDS', 'DATA_OBFSC', 'DATA_AGG')):
        '''Generate authorization to use an i2b2 project.
        '''
        log.debug('generate authorization for: %s', (uid, full_name))
        ds = self._datasrc()

        t = func.now()
        auth = str(self._uuidgen.uuid4())
        pw_hash = hexdigest(auth)

        # TODO: consider factoring out the "update the change_date
        # whenever you set a field" aspect of Audited.
        try:
            me = ds.query(User).filter(User.user_id == uid).one()
        except orm.exc.NoResultFound:
            me = User(user_id=uid, full_name=full_name,
                      entry_date=t, change_date=t, status_cd='A',
                      password=pw_hash,
                      # Related UserRole records might exist
                      # even though there is no User record.
                      roles=ds.query(UserRole).filter_by(user_id=uid).all())
            log.info('adding: %s', me)
            ds.add(me)
        else:
            log.info('found: %s', me)
            me.password, me.status_cd, me.change_date = pw_hash, 'A', t
        # http://docs.sqlalchemy.org/en/rel_0_8/orm/query.html?highlight=query.update#sqlalchemy.orm.query.Query.update # noqa
        ds.query(UserRole).filter(and_(UserRole.user_id == uid,
            UserRole.user_role_cd.in_(list(roles)))).\
            delete(synchronize_session='fetch')

        #If a user has permissions to REDCap i2b2 project,
        # also grant permissions to default project #2111
        for project in set([project_id, DEFAULT_PID]):
            for r in roles:
                myrole = UserRole(user_id=uid, project_id=project,
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


def proj_desc_for(rc_pids):
    """Encode a set of REDCap project IDs in an I2B2 project description.

    >>> proj_desc_for((1, 15, 2))
    'redcap_1_2_15'
    """
    return 'redcap_' + ('_'.join([str(pid) for pid in sorted(rc_pids)]))


class I2B2Account(ocap_file.Token):
    def __init__(self, pm, agent, project_id):
        self.__pm = pm
        self.__agent = agent
        self._project_id = project_id

    def __repr__(self):
        return 'Access(%s)' % self.__agent

    def creds(self):
        agent = self.__agent
        key, u = self.__pm.authz(agent.cn, agent.full_name(), self._project_id)
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


def _mock_i2b2_projects(ds, id_descs):
    '''Mock up i2b2 projects
    '''
    for pid, desc in id_descs:
        ds.add(Project(project_id='REDCap_%s' % pid,
                       project_description=desc))
    ds.commit()


def _mock_i2b2_proj_usage(ds, assignments):
    '''Mock up assigning REDCap metadata to i2b2 projects.
    '''
    for (i2b2_id, rc_pid) in assignments:
        ds.query(Project).filter_by(project_id='REDCap_' + i2b2_id).\
            update({"project_description": 'redcap_%s' % rc_pid})
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
    t, _ = pm.i2b2_project(rc_pids.split(','))
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

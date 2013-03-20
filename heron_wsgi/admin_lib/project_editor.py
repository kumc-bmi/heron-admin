'''project_editor -- list and edit projects by one investigator

>>> import medcenter
>>> mc, dr = noticelog.Mock.make([
...     medcenter.MedCenter, noticelog.DecisionRecords])
>>> req = medcenter.MockRequest()
>>> _ = mc.authenticated('john.smith', req)
>>> js = mc.idbadge(req.context)

>>> import pprint
>>> ed = ProjectEditor(dr, js)
>>> pprint.pprint(ed.about_projects())
[(u'6373469799195807417',
  (John Smith <john.smith>,
   [Some One <some.one>, ? <carol.student>],
   {u'approve_kuh': u'1',
    u'approve_kumc': u'1',
    u'approve_kupi': u'1',
    u'date_of_expiration': u'',
    u'full_name': u'John Smith',
    u'name_etc_1': u'Some One',
    u'project_title': u'Cure Warts',
    u'user_id': u'john.smith',
    u'user_id_1': u'some.one',
    u'user_id_2': u'carol.student'}))]
>>> pprint.pprint(ed.about_projects(inv=False))
[]
'''

from injector import inject

from ocap_file import Token
import noticelog


class ProjectEditor(Token):
    @inject(dr=noticelog.DecisionRecords)
    def __init__(self, dr, badge):
        self.__dr = dr
        self._badge = badge

    def about_projects(self, inv=True):
        dr = self.__dr
        return [(sponsorship.record,
                 dr.decision_detail(sponsorship.record))
                for sponsorship in dr.sponsorships(self._badge.cn, inv)]

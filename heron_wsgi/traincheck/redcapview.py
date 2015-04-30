'''redcapview -- a row-modelling view of data from the redcap_data EAV table
'''

from sqlalchemy import MetaData, Table, Column
from sqlalchemy import Integer, String
from sqlalchemy import select, text, and_


redcap_meta = MetaData()

redcap_data = Table('redcap_data', redcap_meta,
                    Column(u'project_id', Integer(),
                           nullable=False, default=text(u"'0'"),
                           primary_key=True),
                    Column(u'event_id', Integer(), primary_key=True),
                    Column(u'record', String(), primary_key=True),
                    Column(u'field_name', String(),
                           primary_key=True),
                    Column(u'value', String()),
                    schema='redcap'
                    )


def in_schema(name,
              meta=redcap_meta,
              t=redcap_data):
    tt = t.tometadata(meta)
    tt.schema = name
    return tt


def unpivot(project_id, field_names,
            record=False,
            redcap_data=redcap_data):
    '''
    >>> print unpivot(4688, ['username', 'expired', 'course'], record=True)
    ... # doctest: +NORMALIZE_WHITESPACE
    SELECT username.record,
           username.value AS username,
           expired.value AS expired,
           course.value AS course
    FROM redcap.redcap_data AS username,
         redcap.redcap_data AS expired,
         redcap.redcap_data AS course
    WHERE username.project_id = :project_id_1
      AND username.field_name = :field_name_1
      AND expired.project_id = :project_id_2
      AND expired.field_name = :field_name_2
      AND course.project_id = :project_id_3
      AND course.field_name = :field_name_3
      AND username.record = expired.record
      AND expired.record = course.record
    '''
    if not field_names:
        raise ValueError(field_names)

    froms = [(n, redcap_data.alias(n)) for n in field_names]
    cols = ([froms[0][1].c.record] if record else []) + [
        frm.c.value.label(n) for (n, frm) in froms]

    project = [clause for (n, frm) in froms
               for clause in
               [frm.c.project_id == project_id,
                frm.c.field_name == n]]
    join = [froms[ix][1].c.record == froms[ix + 1][1].c.record
            for ix in range(len(froms) - 1)]

    return select(cols, and_(*project + join),
                  from_obj=[f for (n, f) in froms])

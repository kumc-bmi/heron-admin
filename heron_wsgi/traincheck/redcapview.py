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
    FROM
    (SELECT rd.record AS record, rd.value AS value
    FROM redcap.redcap_data AS rd
    WHERE rd.project_id = :project_id_1 AND rd.field_name = :field_name_1)
    AS username,
    (SELECT rd.record AS record, rd.value AS value
    FROM redcap.redcap_data AS rd
    WHERE rd.project_id = :project_id_2 AND rd.field_name = :field_name_2)
    AS expired,
    (SELECT rd.record AS record, rd.value AS value
    FROM redcap.redcap_data AS rd
    WHERE rd.project_id = :project_id_3 AND rd.field_name = :field_name_3)
    AS course
    WHERE username.record = expired.record AND expired.record = course.record
    '''
    if not field_names:
        raise ValueError(field_names)

    rd = redcap_data.alias('rd')

    def field_query(f):
        return (select([rd.c.record,
                        rd.c.value])
                .where(and_(rd.c.project_id == project_id,
                            rd.c.field_name == f))
                .alias(f))

    fqs = [field_query(n) for n in field_names]
    cols = ([fqs[0].c.record] if record else []) + [
        fq.c.value.label(fq.name) for fq in fqs]

    where = and_(*[fqs[ix].c.record == fqs[ix + 1].c.record
                   for ix in range(len(fqs) - 1)])

    return select(cols, where, from_obj=fqs)

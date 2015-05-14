from collections import namedtuple
import csv
import logging
import xml.etree.ElementTree as ET

log = logging.getLogger(__name__)

from lalib import maker


def readRecords(fp):
    reader = csv.reader(fp)
    header = reader.next()
    R = namedtuple('R', header)
    return [R(*row) for row in reader]


def put(dbtrx, records):
    exemplar = records.next()
    tuple_type = exemplar.__class__
    et = ExportTable(dbtrx,
                     tuple_type.__name__,
                     tuple_type._fields)
    et.recreate()
    return et.insert([exemplar] + list(records)), tuple_type


def docToRecords(relation_doc,
                 cols=None):
    r'''Given a record-oriented XML document, generate namedtuple per record.

    >>> markup = """
    ... <NewDataSet>
    ...   <CRS>
    ...     <MemberID>123</MemberID>
    ...     <intScore>96</intScore>
    ...   </CRS>
    ...   <CRS>
    ...     <MemberID>124</MemberID>
    ...     <intScore>91</intScore>
    ...   </CRS>
    ... </NewDataSet>
    ... """

    >>> doc = ET.fromstring(markup)
    >>> list(docToRecords(doc))
    [CRS(MemberID='123', intScore='96'), CRS(MemberID='124', intScore='91')]

    >>> docToRecords(ET.fromstring('<doc/>'))
    Traceback (most recent call last):
      ...
    StopIteration
    '''
    exemplar = iter(relation_doc).next()
    relation_name = exemplar.tag
    if not cols:
        cols = [child.tag for child in exemplar]
    R = namedtuple(relation_name, cols)
    default = R(*[None] * len(cols))

    def record(elt):
        bindings = [(child.tag, child.text) for child in elt]
        return default._replace(**dict(bindings))

    return (record(child) for child in relation_doc)


def mock_xml_records(template, qty):
    n = [10]

    def num():
        n[0] += 17
        return n[0]

    def ymd():
        n[0] += 29
        return '%04d-%02d-%02dT12:34:56' % (
            2000, n[0] % 12 + 1, (n[0] * 3) % 26 + 1)

    def mdy():
        n[0] += 29
        return '%02d/%02d/%02d' % (
            n[0] % 12 + 1, (n[0] * 3) % 26 + 1, 11)

    def txt(tag):
        n[0] += 13
        return (
            # Please excuse the abstraction leak...
            'Basic/Refresher Course - Human Subjects Research'
            if tag == 'strCompletionReport' and n[0] % 3
            else 's' * (n[0] % 5) + 't' * (n[0] % 7))

    def record_markup():
        record = ET.fromstring(template)
        for field in record:
            if field.text == '12345':
                field.text = str(num())
            elif field.text == '2014-05-06T19:15:48':
                field.text = ymd()
            elif field.text == '09/09/14':
                field.text = mdy()
            else:
                field.text = txt(field.tag)

        return ET.tostring(record)

    return ("<NewDataSet>"
            + '\n'.join(record_markup()
                        for _ in range(qty))
            + "</NewDataSet>")


def tableTuple(name, description):
    cols = [d[0] for d in description]

    return namedtuple(name, cols)


@maker
def ExportTable(dbtrx, name, cols):
    create_stmt, insert_stmt = sql_for(name, cols)

    def recreate(_):
        log.info('(re-)creating %s: %s',
                 name, create_stmt)
        with dbtrx() as ddl:
            ddl.execute('drop table if exists %s' % name)
            ddl.execute(create_stmt)

    def insert(_, rows):
        with dbtrx() as dml:
            dml.executemany(insert_stmt, rows)
        log.info('inserted %d rows into %s', len(rows), name)
        return len(rows)

    return [recreate, insert], dict(name=name)


def sql_for(table, cols):
    '''
    >>> c, i = sql_for('t1', ['cx', 'cy', 'cz'])
    >>> print c
    create table t1 ( cx, cy, cz )
    >>> print i
    insert into t1 (cx, cy, cz) values (?, ?, ?)
    '''
    create_stmt = 'create table %s ( %s )' % (
        table,
        ', '.join(cols))
    insert_stmt = 'insert into %s (%s) values (%s)' % (
        table,
        ', '.join(cols),
        ', '.join(['?'] * len(cols)))
    return create_stmt, insert_stmt
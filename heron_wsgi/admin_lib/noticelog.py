'''noticelog -- maintain a log of email notices in a table
'''

from sqlalchemy import Table, Column
from sqlalchemy.types import Integer, String, VARCHAR, TIMESTAMP
from sqlalchemy.schema import ForeignKey

from orm_base import Base

notice_log = Table('notice_log', Base.metadata,
                   Column('id', Integer, primary_key=True),
                   Column('record', VARCHAR(100),
                          ForeignKey('redcap_data.record')),
                   Column('timestamp', TIMESTAMP()),
                   schema='droctools',
                   mysql_engine='InnoDB',
                   mysql_collate='utf8_unicode_ci'
                   )

if __name__ == '__main__':
    print "schema:"
    from sqlalchemy.schema import CreateTable
    print CreateTable(noticelog.notice_log, bind=hr._engine)


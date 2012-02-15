'''noticelog -- maintain a log of email notices in a table
'''

from sqlalchemy import Table, Column, create_engine
from sqlalchemy.types import Integer, VARCHAR, TIMESTAMP
from sqlalchemy.schema import ForeignKey

from redcapdb import Base

notice_log = Table('notice_log', Base.metadata,
                   Column('id', Integer, primary_key=True),
                   Column('record', VARCHAR(100),
                          ForeignKey('redcap_data.record')),
                   Column('timestamp', TIMESTAMP()),
                   schema='droctools',
                   mysql_engine='InnoDB',
                   mysql_collate='utf8_unicode_ci')

if __name__ == '__main__':
    print "schema:"
    from sqlalchemy.schema import CreateTable
    print CreateTable(notice_log, bind=create_engine('sqlite:///'))

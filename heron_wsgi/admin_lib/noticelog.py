'''noticelog -- maintain a log of email notices in a table
----------------------------------------------------------

The following table is used to log notices::

  >>> from sqlalchemy import create_engine
  >>> from sqlalchemy.schema import CreateTable
  >>> print CreateTable(notice_log, bind=create_engine('sqlite:///'))
  ... #doctest: +NORMALIZE_WHITESPACE
  CREATE TABLE notice_log (
      id INTEGER NOT NULL,
      record VARCHAR(100),
      timestamp TIMESTAMP,
      PRIMARY KEY (id),
      FOREIGN KEY(record) REFERENCES redcap_data (record)
  )

'''

from sqlalchemy import Table, Column
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

'''sqlaview -- sqlalchemy view support
   ref: ack: https://bitbucket.org/zzzeek/sqlalchemy/wiki/UsageRecipes/Views
'''

from sqlalchemy import DateTime
from sqlalchemy.schema import DDLElement
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.expression import (
    FunctionElement, Executable, ClauseElement)


class CreateView(Executable, ClauseElement):
    def __init__(self, name, query, schema):
        self.name = name
        self.query = query
        self.schema = schema


class DropView(DDLElement):
    def __init__(self, name, schema):
        self.name = name
        self.schema = schema


@compiles(CreateView)
def compile_create_view(element, compiler, **kw):
    """Generate a create statement for this view."""

    if isinstance(element.query, basestring):
        query = element.query
    else:
        if hasattr(element.query, "statement"):
            statement = element.query.statement
        else:
            statement = element.query

        # ref: How do I render SQL expressions as strings,
        # possibly with bound parameters inlined?
        # http://docs.sqlalchemy.org/en/improve_toc/faq/sqlexpressions.html#faq-sql-expression-string  # noqa
        query = compiler.process(statement, literal_binds=True)

    pfx, sep = ((compiler.preparer.quote(element.schema, ""), '.')
                if element.schema else ('', ''))

    if compiler.dialect.paramstyle in ('format', 'pyformat'):
        query = query.replace('%', '%%')

    stmt = "CREATE VIEW %s%s%s AS %s" % (
        pfx, sep,
        compiler.preparer.quote(element.name, ""),
        query,
    )

    return stmt


@compiles(DropView)
def compile3(element, compiler, **kw):
    pfx, sep = ((compiler.preparer.quote(element.schema, ""), '.')
                if element.schema else ('', ''))
    return "DROP VIEW IF EXISTS %s%s%s" % (pfx, sep, element.name)


class fyears_after(FunctionElement):
    '''Fiscal years after

    fyears_after(t, n, fy_basis_months, fy_start_mm_dd)

    e.g.
    fyears_after(events.when, 3, -6, '07-01')
    '''
    type = DateTime()
    name = 'fyears_after'


@compiles(fyears_after)
def fyear_after_default(element, compiler, **kw):
    return compiler.visit_function(element)


@compiles(fyears_after, 'sqlite')
def fyears_after_sqlite(element, compiler, **kw):
    '''Compile fyears_after for sqlite.

    >>> import sqlalchemy as sa
    >>> meta = sa.MetaData()

    >>> events = sa.Table('events', meta,
    ...                   sa.Column('what', sa.String),
    ...                   sa.Column('when', sa.Date))
    >>> q = sa.select([fyears_after(events.c.when, 3, -6, '07-01')])

    >>> memdb = sa.create_engine('sqlite:///')
    >>> print q.compile(memdb)
    ... # doctest: +NORMALIZE_WHITESPACE
    SELECT datetime(
              strftime('%Y-' || '07-01',
                       datetime(events."when", '-6 months')),
              '+3 years')
    FROM events
    '''
    # 1. add basis months
    # 2. extract year
    # 3. append fy_start mm-dd
    # 4. add n years
    return """
        datetime(
          strftime('%%Y-' || %(fy_start)s,
                   datetime(%(t0)s, '%(basis)s months')),
          '+%(n)s years')
        """.strip() % _parts(compiler, element.clauses)


def _parts(compiler, clauses):
    [t0, n, fy_basis, fy_start] = list(clauses)
    return dict(fy_start=compiler.process(fy_start, literal_binds=True),
                t0=compiler.process(t0, literal_binds=True),
                basis=compiler.process(fy_basis, literal_binds=True),
                n=compiler.process(n, literal_binds=True))


@compiles(fyears_after, 'mysql')
def fyears_after_mysql(element, compiler, **kw):
    '''Compile fyears_after for mysql.

    >>> import sqlalchemy as sa
    >>> meta = sa.MetaData()

    >>> events = sa.Table('events', meta,
    ...                   sa.Column('what', sa.String),
    ...                   sa.Column('when', sa.Date))
    >>> q = sa.select([fyears_after(events.c.when, 3, -6, '07-01')])

    >>> db = sa.create_engine('mysql://')
    >>> print q.compile(db)
    ... # doctest: +NORMALIZE_WHITESPACE
    SELECT str_to_date(
          concat(cast(round(
             period_add(date_format(events.`when`, '%Y%m'), -6 + 12 * 3)
             / 100) as char), '-', '07-01'), '%Y-%m-%d')
    FROM events

    '''
    # 1. format t0 as period: YYYYMM
    # 2. add basis + 12 * n months
    # 3. divide period by 100 to get year
    # 4. append fy_start mm-dd
    # 5. convert str_to_date
    return """
    str_to_date(
      concat(cast(round(
         period_add(date_format(%(t0)s, '%%Y%%m'), %(basis)s + 12 * %(n)s)
         / 100) as char), '-', %(fy_start)s), '%%Y-%%m-%%d')
    """.strip() % _parts(compiler, element.clauses)

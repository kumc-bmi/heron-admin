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
    '''
    type = DateTime()
    name = 'fyears_after'


@compiles(fyears_after)
def fyear_after_default(element, compiler, **kw):
    return compiler.visit_function(element)


@compiles(fyears_after, 'sqlite')
def fyear_after_sqlite(element, compiler, **kw):
    # 1. add basis months
    # 2. extract year
    # 3. append fy_start mm-dd
    # 4. add n years
    return """
        datetime(
          strftime('%%Y-' || %(fy_start)s,
                   datetime(%(t0)s, '%(basis)s months')),
          '+%(n)s years')
        """ % _parts(compiler, element.clauses)


def _parts(compiler, clauses):
    [t0, n, fy_basis, fy_start] = list(clauses)
    return dict(fy_start=compiler.process(fy_start, literal_binds=True),
                t0=compiler.process(t0, literal_binds=True),
                basis=compiler.process(fy_basis, literal_binds=True),
                n=compiler.process(n, literal_binds=True))


@compiles(fyears_after, 'mysql')
def fyear_after_mysql(element, compiler, **kw):
    # 1. format t0 as period: YYYYMM
    # 2. add basis + 12 * n months
    # 3. divide period by 100 to get year
    # 4. append fy_start mm-dd
    # 5. convert str_to_date
    return """
    str_to_date(
      concat(cast(round(
         period_add(date_format(t0, '%Y%m'), basis + 12 * n)
         / 100) as char), '-', fy_start), '%Y-%m-%d')
    """ % _parts(compiler, element.clauses)

'''sqlaview -- sqlalchemy view support

'''

from sqlalchemy.schema import DDLElement
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.expression import (
    Executable, ClauseElement)


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

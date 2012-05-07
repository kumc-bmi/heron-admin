import pkg_resources
import csv


def records(data_fn='mockDirectory.csv'):
    '''
    >>> [(r['kumcPersonFaculty'], r['cn']) for r in list(records())]
    ... #doctest: +NORMALIZE_WHITESPACE
    [('Y', 'john.smith'),
     ('N', 'bill.student'),
     ('N', 'carol.student'),
     ('N', 'some.one'),
     ('N', 'big.wig')]
    '''
    for r in csv.DictReader(pkg_resources.resource_stream(__name__, data_fn)):
        yield r

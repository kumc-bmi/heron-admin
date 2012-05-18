'''jndi_util -- just enough jboss JNDI to get an Oracle connection.

.. todo:: consider factoring out of rgate/i2b2hive.py
'''

from lxml import etree


def ds_access(jboss_deploy, jndi_name):
    '''Parse connection details of a jboss datasource by jndi-name.

    :param jboss_deploy: a read-capability to a jboss deploy directory.

    >>> import os
    >>> here = Readable('.', os.path, os.listdir, open)

    >>> ds_access(here, 'QueryToolBLUEHERONDS')
    ('BLUEHERONdata', 'xyzpdq', 'bmidev1', '1521', 'bmid')

    Note case sensitivity:

    >>> ds_access(here, 'QueryToolBlueHeronDS')
    Traceback (most recent call last):
      ...
    KeyError: 'QueryToolBlueHeronDS'

    >>> ds_access(here.subRdFile('does_not_exist'), 'BLUEHERONdata')
    Traceback (most recent call last):
      ...
    OSError: [Errno 2] No such file or directory: './does_not_exist'

    :raises: XMLSyntaxError on failure to parse XML files therein,
    '''
    for f in jboss_deploy.subRdFiles():
        if not f.fullpath().endswith('-ds.xml'):
            continue
        doc = etree.parse(f.inChannel())
        src_expr = ('/datasources/local-tx-datasource[jndi-name/text()="%s"]' %
                    jndi_name)
        try:
            src = doc.xpath(src_expr)[0]
            un = src.xpath('user-name/text()')[0]
            pw = src.xpath('password/text()')[0]
            url = src.xpath('connection-url/text()')[0]
            host, port, sid = url.split('@', 1)[1].split(':', 2)
            return un, pw, host, port, sid
        except IndexError:
            pass

    raise KeyError(jndi_name)


def edef(*methods):
    '''imitate E method suite definition
    '''
    lookup = dict([(f.__name__, f) for f in methods])

    class EObj(object):
        def __getattr__(self, n):
            if n in lookup:
                return lookup[n]
            raise AttributeError(n)

    return EObj()


def Readable(path, os_path, os_listdir, openf):
    '''
    >>> import os
    >>> Readable('.', os.path, os.listdir, open).isDir()
    True
    '''
    def isDir():
        return os_path.isdir(path)

    def exists():
        return os_path.exists(path)

    def subRdFiles():
        return (Readable(os_path.join(path, n), os_path, os_listdir, openf)
                for n in os_listdir(path))

    def subRdFile(n):
        return Readable(os_path.join(path, n), os_path, os_listdir, openf)

    def inChannel():
        return openf(path)

    def getBytes():
        return openf(path).read()

    def fullpath():
        return os_path.abspath(path)

    return edef(isDir, exists, subRdFiles, subRdFile, inChannel,
                getBytes, fullpath)


class Editable(object):
    #ro : readable;
    #subEdFiles : unit -> editable list;
    #subEdFile : string -> editable;
    #outChannel : unit -> out_channel;
    #setBytes : string -> unit;
    #mkDir : unit -> unit;
    #createNewFile : unit -> unit;
    #delete : unit -> unit;
    pass

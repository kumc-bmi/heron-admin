'''lalib -- least-authority I/O support

Capability-based security is useful for establishing security
properties of a large system in terms of properties of the parts.  The
object capability discipline requires `absolute encapsulation`__, but
python's classes don't encapsulate their instance state. "We're all
consenting adults here," is the tag line.  So we provide a `@maker`
decorator for building encapsulated objects.  It turns a function that
returns methods and an attribute dictionary into a constructor for an
encapsulated class.

__ http://erights.org/elib/capability/ode/ode-capabilities.html#encap

For example, we can encapsulate a secret in an object that can compute
keyed hashes of the secret without ever revealing the secret::

>>> import hashlib

>>> @maker
... def Keeper(secret):
...     def hmac(_, salt):
...         x = hashlib.md5()
...         x.update(secret)
...         x.update(salt)
...         return x.hexdigest()
...     return [hmac], {}

>>> k1 = Keeper('abracadabra')
>>> k1.hmac('salt1')
'0fddd18ba1aac994c50c8050c917df72'

>>> k1.secret
Traceback (most recent call last):
  ...
AttributeError: 'Keeper' object has no attribute 'secret'

'''

from posixpath import basename, splitext, join
from functools import wraps


def maker(wrapped):
    @wraps(wrapped)
    def make(*args, **kwargs):
        methods, properties = wrapped(*args, **kwargs)
        bases = (object,)
        maker = type(wrapped.__name__, bases,
                     dict(properties.items() +
                          [(m.__name__, m) for m in methods]))
        return maker()
    return make


@maker
def Rd(path, open_rd, listdir):
    '''Yet another version of `Readable()`__
    __ https://bitbucket.org/DanC/blackknightcap/src/tip/ocap/lafile.py
    '''
    def __div__(_, sub):
        fullsub = join(path, sub)
        if not fullsub.startswith(path):
            raise IOError('no upward traversal')

        return Rd(fullsub, open_rd, listdir)

    def open(_):
        return open_rd(path)

    def iterdir(_):
        return (Rd(join(path, p), open_rd, listdir)
                for p in listdir(path))

    return [__div__, open, iterdir], dict(
        name=basename(path),
        suffix=splitext(path)[1])

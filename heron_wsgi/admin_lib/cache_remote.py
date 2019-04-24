'''cache_remote -- cache answers to remote queries
'''

import logging

log = logging.getLogger(__name__)


class Cache(object):
    def __init__(self, now):
        self.__now = now
        self._cache = {}
        ix = 1  # was global mutable state. ew.
        log.info('%s@%s cache initialized',
                 self.__class__.__name__, ix)

    def _query(self, k, thunk, label=None):
        tnow = self.__now()
        try:
            expire, v = self._cache[k]
        except KeyError:
            pass
        else:
            if expire > tnow:
                return v

        # We're taking the time to go over the network; now is
        # a good time to prune the cache.
        self._prune(tnow)

        log.info('%s query for %s', label, k)
        ttl, v = thunk()
        log.info('... cached until %s', tnow + ttl)
        self._cache[k] = (tnow + ttl, v)
        return v

    def _prune(self, tnow):
        for k, (t, _) in self._cache.items():
            if t <= tnow:
                del self._cache[k]

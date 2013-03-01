'''cache_remote -- cache answers to remote queries
'''

import logging

log = logging.getLogger(__name__)


class Cache(object):
    def __init__(self, now):
        self.__now = now
        self._cache = {}

    def _query(self, k, thunk, label=None):
        tnow = self.__now()
        try:
            expire, v = self._cache[k]
            log.debug('cache hit? %s %s %s', expire, tnow, expire > tnow)
            if expire > tnow:
                return v
        except KeyError:
            pass

        # We're taking the time to go over the network; now is
        # a good time to prune the cache.
        for k, (t, v) in self._cache.items():
            if t <= tnow:
                del self._cache[k]

        log.info('%s query for %s', label, k)
        ttl, v = thunk()
        log.info('... cached until %s', tnow + ttl)
        self._cache[k] = (tnow + ttl, v)
        return v

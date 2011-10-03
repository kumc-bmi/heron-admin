'''logwatch.py -- invoke HTTP post each time a mysql trigger creates a file

Note `MySQL :: MySQL 5.6 Reference Manual :: 12.2.9 SELECT Syntax`__:

  file_name cannot be an existing file, which among other things
  prevents files such as /etc/passwd and database tables from being
  destroyed.

__ http://dev.mysql.com/doc/refman/5.6/en/select.html

So we delete the file each time we detect it was created.

'''

import sys
import os
import ConfigParser
import urllib2
import logging

# http://pypi.python.org/pypi/pyinotify/0.9.2
# b63c14f8f8d953432e2040a013487c2f
import pyinotify

CONFIG_SECTION='oversight_survey'
log = logging.getLogger(__name__)

def main(argv=sys.argv):
    ini = argv[1]
    rt = ConfigParser.SafeConfigParser()
    rt.read(ini)
    logging.basicConfig(**dict(rt.items(CONFIG_SECTION)))
    watch(rt.get(CONFIG_SECTION, 'trigger_log'),
          rt.get(CONFIG_SECTION, 'trigger_url'),
          urllib2.build_opener())


class Trigger(pyinotify.ProcessEvent):
    def my_init(self, post_url, ua):
        self._post_url = post_url
        self._ua = ua

    def process_default(self, event):
        log.info("creation detected: %s ; posting now" % event.pathname)
        os.remove(event.pathname)
        log.info('removed %s' % event.pathname) 
        try:
            self._ua.open(self._post_url, data=event.pathname)
        except IOError, e:
            log.warn('post to %s failed: %s' % (self._post_url, e))


def watch(fn, post_url, urlopener):
    wm = pyinotify.WatchManager()
    t = Trigger(post_url=post_url, ua=urlopener)
    notifier = pyinotify.Notifier(wm, default_proc_fun=t)
    wm.add_watch(fn, pyinotify.IN_CREATE, rec=True)
    notifier.loop()


if __name__ == '__main__':
    main()

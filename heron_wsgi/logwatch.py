
# http://pypi.python.org/pypi/pyinotify/0.9.2
# b63c14f8f8d953432e2040a013487c2f
import pyinotify
import sys

def main(argv=sys.argv):
    logfn = argv[1]
    watch(logfn)

def watch(fn):
    wm = pyinotify.WatchManager()
    notifier = pyinotify.Notifier(wm, default_proc_fun=pyinotify.ProcessEvent())
    wm.add_watch(fn, pyinotify.IN_MODIFY)
    notifier.loop(callback=post)

def post(notifier):
    print "@@modification detected; post now"
    return False

if __name__ == '__main__':
    main()

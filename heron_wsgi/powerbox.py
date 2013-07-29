'''powerbox -- control of authority in HERON Admin.

cf http://wiki.erights.org/wiki/Walnut/Secure_Distributed_Computing/Capability_Patterns#Powerbox_Capability_Manager
'''

import subprocess

import stats


class LinuxMachine(stats.Machine):
    durations = (1, 5, 15)  # minutes, per man uptime

    def load(self):
        times = self._parse(check_output(['uptime']))
        return zip(self.durations, times)

    @classmethod
    def _parse(cls, uptime_output):
        '''
        >>> o = ' 15:46:33 up 2 days,  6:25,  9 users,  load average: 0.02, 0.75, 0.5'
        >>> [round(x, 2) for x in LinuxMachine._parse(o)]
        [0.02, 0.75, 0.5]
        '''
        return map(float, uptime_output.split('load average: ', 1)[1].split(', '))


def check_output(args):
    '''a la subprocess.check_output from python 2.7
    '''
    sub = subprocess.Popen(args, stdout=subprocess.PIPE)
    out, _err = sub.communicate()
    if sub.returncode != 0:
        raise subprocess.CalledProcessError(sub.returncode)
    return out

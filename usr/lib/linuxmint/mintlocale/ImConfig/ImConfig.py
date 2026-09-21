# ImConfig.py (c) 2012-2014 Canonical
# Author: Gunnar Hjalmarsson <gunnarhj@ubuntu.com>
#
# Released under the GPL
#

import os
import subprocess


class ImConfig(object):

    def __init__(self):
        self.legacy = False
        self.report = ''

    def init(self):
        # Kept out of __init__ because im-config takes its time: the thread
        # which reads the configuration calls this, so the window does not wait
        self.report = self.run(['-r'])

        # im-config 1.0 renamed the options this was written against: -l, -l -a,
        # -m and -n became -i, -p, -r and -w, and the old ones are now silently
        # ignored. Only the new one answers -r with a report, so that tells the
        # two apart, whatever the version number says.
        self.legacy = 'IM framework' not in self.report

    def run(self, args):
        # The locale is left alone on purpose: im-config picks the framework a
        # language needs out of LC_CTYPE, so a forced LC_ALL would change the
        # answer for the CJK locales. The lines parsed below are not translated.
        try:
            return subprocess.check_output(['im-config'] + args, stderr=subprocess.DEVNULL).decode()
        except (OSError, subprocess.SubprocessError):
            return ''

    def available(self):
        return os.path.exists('/usr/bin/im-config')

    def getAvailableInputMethods(self):
        inputMethods = self.run(['-l'] if self.legacy else ['-i']).split()
        return sorted(inputMethods)

    def getAllInputMethods(self):
        inputMethods = self.run(['-l', '-a'] if self.legacy else ['-p']).split()
        return sorted(inputMethods)

    def getReportedConfig(self):
        """The three values "im-config -m" used to give, out of the "im-config -r" report"""
        userConfig = 'missing'
        autoConfig = ''
        setConfig = ''
        configured = False
        for line in self.report.splitlines():
            if line.startswith('Configuration file:'):
                configured = '(removed)' not in line
            elif line.startswith('IM framework (set):'):
                setConfig = line.split(':', 1)[1].strip()
            elif line.startswith('IM framework (auto):'):
                autoConfig = line.split(':', 1)[1].strip()

        if configured and setConfig != 'auto':
            userConfig = setConfig

        # The report does not carry the mode of /etc/default/im-config, and the
        # automatic value is the one wanted for every mode but 'cjkv'
        return ('default', userConfig, autoConfig)

    def getCurrentInputMethod(self):
        if self.legacy:
            # Output from the comamand "im-config -m" is different between Trusty (17.x) and Xenial (18.x), but the first three values are the same
            splits = self.run(['-m']).split()
            if len(splits) < 3:
                splits = ['default', 'missing', '']
            (systemConfig, userConfig, autoConfig) = splits[0:3]
        else:
            (systemConfig, userConfig, autoConfig) = self.getReportedConfig()

        if userConfig != 'missing':
            return userConfig

        """
        no saved user configuration
        let's ask the system and save the system configuration as the user ditto
        """
        system_conf = ''
        if os.path.exists('/usr/bin/fcitx'):
            # Ubuntu Kylin special
            system_conf = 'fcitx'
        elif systemConfig == 'default':
            # Using the autoConfig value might be incorrect if the mode in
            # /etc/default/im-config is 'cjkv'. However, as from im-config 0.24-1ubuntu1
            # the mode is 'auto' for all users of language-selector-gnome.
            system_conf = autoConfig
        elif os.path.exists('/etc/X11/xinit/xinputrc'):
            for line in open('/etc/X11/xinit/xinputrc'):
                if line.startswith('run_im'):
                    system_conf = line.split()[1]
                    break
        if not system_conf:
            system_conf = autoConfig
        self.setInputMethod(system_conf)
        return system_conf

    def setInputMethod(self, im):
        subprocess.call(['im-config', '-n' if self.legacy else '-w', im])

if __name__ == '__main__':
    im = ImConfig()
    im.init()
    print('available input methods: %s' % im.getAvailableInputMethods())
    print('current method: %s' % im.getCurrentInputMethod())
    print("setting method 'fcitx'")
    im.setInputMethod('fcitx')
    print('current method: %s' % im.getCurrentInputMethod())
    print('removing ~/.xinputrc')
    im.setInputMethod('REMOVE')

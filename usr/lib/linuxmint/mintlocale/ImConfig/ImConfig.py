# ImConfig.py (c) 2012-2014 Canonical
# Author: Gunnar Hjalmarsson <gunnarhj@ubuntu.com>
#
# Released under the GPL
#

import os
import subprocess


class ImConfig(object):

    def __init__(self):
        pass

    def available(self):
        return os.path.exists('/usr/bin/im-config')

    def getAvailableInputMethods(self):
        inputMethods = subprocess.check_output(['im-config', '-l']).decode().split()
        return sorted(inputMethods)

    def getAllInputMethods(self):
        inputMethods = subprocess.check_output(['im-config', '-l', '-a']).decode().split()
        return sorted(inputMethods)

    def getCurrentInputMethod(self):
        # Output from the comamand "im-config -m" is different between Trusty (17.x) and Xenial (18.x), but the first three values are the same
        splits = subprocess.check_output(['im-config', '-m']).decode().split()
        (systemConfig, userConfig, autoConfig) = splits[0:3]

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
        subprocess.call(['im-config', '-n', im])

if __name__ == '__main__':
    im = ImConfig()
    print('available input methods: %s' % im.getAvailableInputMethods())
    print('current method: %s' % im.getCurrentInputMethod())
    print("setting method 'fcitx'")
    im.setInputMethod('fcitx')
    print('current method: %s' % im.getCurrentInputMethod())
    print('removing ~/.xinputrc')
    im.setInputMethod('REMOVE')

#!/usr/bin/python3
"""Registration of the locales installed on the system.

Compiling a locale with localedef is not enough to install it: on Debian and
Ubuntu the locale archive is rebuilt from /etc/locale.gen, so a locale which
is not listed there is lost at the first locale-gen run, be it a glibc
upgrade, a dpkg-reconfigure locales or the user. Ubuntu also collects entries
from /var/lib/locales/supported.d, but reads /etc/locale.gen as well, so that
one file is enough for both.

Distributions with no locale-gen at all keep whatever localedef compiled, and
there the archive is the only registry there is.
"""

import os
import subprocess

LOCALE_GEN_PATH = "/etc/locale.gen"
LOCALE_GEN = "/usr/sbin/locale-gen"
I18N_SUPPORTED_PATH = "/usr/share/i18n/SUPPORTED"

# Where older versions registered the locales instead
SUPPORTED_PATH = "/var/lib/locales/supported.d/mintlocale"


def install_locale(entry):
    """Install a locale, given as a "<name> <charmap>" line of /usr/share/i18n/SUPPORTED"""
    name, charmap = (entry.split() + ["UTF-8"])[:2]

    if os.path.exists(LOCALE_GEN_PATH):
        _migrate_supported()
        _update_locale_gen(name, entry="%s %s" % (name, charmap))
        subprocess.call([LOCALE_GEN, "--keep-existing"])
    else:
        subprocess.call(["localedef", "-f", charmap, "-i", name.split(".")[0], name])


def remove_locale(name):
    """Remove a locale, given by name as listed by localedef --list-archive"""
    if os.path.exists(LOCALE_GEN_PATH):
        _migrate_supported()
        _update_locale_gen(name)
    subprocess.call(["localedef", "--delete-from-archive", name.replace("UTF-8", "utf8")])


def _update_locale_gen(name, entry=None):
    """List the locale in /etc/locale.gen when entry is given, comment it out otherwise"""
    with open(LOCALE_GEN_PATH, "r", encoding="utf-8") as gen_file:
        lines = gen_file.read().splitlines()

    found = False
    content = []
    for line in lines:
        fields = line.lstrip("#").split()
        if fields and fields[0] == name:
            found = True
            content.append(entry if entry else "# %s" % " ".join(fields))
        else:
            content.append(line)

    if entry and not found:
        content.append(entry)

    with open(LOCALE_GEN_PATH, "w", encoding="utf-8") as gen_file:
        gen_file.write("\n".join(content) + "\n")


def _migrate_supported():
    """Move the entries older versions left in supported.d over to /etc/locale.gen

    That file was built with a sed on the archive listing, so the locales whose
    name carries no codeset ended up in it without a charmap, and locale-gen
    rejects those with "Bad entry" at every run.
    """
    if not os.path.exists(SUPPORTED_PATH):
        return

    with open(SUPPORTED_PATH, "r", encoding="utf-8") as supported_file:
        lines = supported_file.read().splitlines()

    for line in lines:
        fields = line.split()
        if not fields:
            continue
        entry = " ".join(fields) if len(fields) > 1 else _supported_entry(fields[0])
        if entry:
            _update_locale_gen(fields[0], entry=entry)

    os.remove(SUPPORTED_PATH)


def _supported_entry(name):
    """The /usr/share/i18n/SUPPORTED line of a locale, charmap included"""
    if os.path.exists(I18N_SUPPORTED_PATH):
        with open(I18N_SUPPORTED_PATH, "r", encoding="utf-8") as supported_file:
            for line in supported_file:
                fields = line.split()
                if fields and fields[0] == name:
                    return " ".join(fields)
    return None

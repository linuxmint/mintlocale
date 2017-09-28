#!/usr/bin/python3

import os
import subprocess
import sys
import gettext
import locale
import codecs

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf

# i18n
APP = 'mintlocale'
LOCALE_DIR = "/usr/share/linuxmint/locale"
locale.bindtextdomain(APP, LOCALE_DIR)
gettext.bindtextdomain(APP, LOCALE_DIR)
gettext.textdomain(APP)
_ = gettext.gettext

FLAG_PATH = "/usr/share/iso-flag-png/%s.png"
FLAG_SIZE = 22

class MintLocale:

    ''' Create the UI '''

    def __init__(self):

        self.selected_language = None

        self.builder = Gtk.Builder()
        self.builder.set_translation_domain("mintlocale")
        self.builder.add_from_file('/usr/share/linuxmint/mintlocale/add.ui')
        self.window = self.builder.get_object("main_window")

        self.builder.get_object("main_window").connect("destroy", Gtk.main_quit)

        self.treeview = self.builder.get_object("treeview_language_list")

        self.builder.get_object("main_window").set_title(_("Add a New Language"))
        self.builder.get_object("main_window").set_icon_name("preferences-desktop-locale")
        self.builder.get_object("main_window").connect("destroy", Gtk.main_quit)
        self.builder.get_object("button_close").connect("clicked", Gtk.main_quit)
        self.builder.get_object("button_install").connect("clicked", self.button_install_clicked)

        ren = Gtk.CellRendererPixbuf()
        column = Gtk.TreeViewColumn("Flags", ren)
        column.add_attribute(ren, "pixbuf", 2)
        ren.set_property('ypad', 5)
        ren.set_property('xpad', 10)
        self.treeview.append_column(column)

        ren = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Languages", ren)
        column.add_attribute(ren, "markup", 0)
        self.treeview.append_column(column)

        self.build_lang_list()

    # Checks for minority languages that have a flag and returns the corresponding flag_path or the unchanged flag_path
    def set_minority_language_flag_path(self, locale_code, flag_path):
        # Get the language code from the locale_code. For example, Basque's locale code can be eu or eu_es or eu_fr, Welsh's cy or cy_gb...
        language_code = locale_code.split("_")[0]

        if language_code == 'ca':
            flag_path = FLAG_PATH % '_catalonia'
        elif language_code == 'cy':
            flag_path = FLAG_PATH % '_wales'
        elif language_code == 'eu':
            flag_path = FLAG_PATH % '_basque'
        elif language_code == 'gl':
            flag_path = FLAG_PATH % '_galicia'

        return flag_path

    def build_lang_list(self):
        self.builder.get_object('button_install').set_sensitive(False)

        model = Gtk.ListStore(str, str, GdkPixbuf.Pixbuf)  # label, locale, flag
        model.set_sort_column_id(0, Gtk.SortType.ASCENDING)

        # Load countries into memory
        self.countries = {}
        with codecs.open('/usr/share/linuxmint/mintlocale/countries', "r", encoding='utf-8') as file:
            for line in file:
                line = line.strip()
                split = line.split("=")
                if len(split) == 2:
                    self.countries[split[0]] = split[1]

        # Load languages into memory
        self.languages = {}
        with codecs.open('/usr/share/linuxmint/mintlocale/languages', "r", encoding='utf-8') as file:
            for line in file:
                line = line.strip()
                split = line.split("=")
                if len(split) == 2:
                    self.languages[split[0]] = split[1]

        if os.path.exists("/usr/share/i18n/SUPPORTED"):
            with codecs.open("/usr/share/i18n/SUPPORTED", "r", encoding="utf-8") as file:
                locales = file.read()
        else:
            locales = u""

        installed = subprocess.check_output("localedef --list-archive | sed s/utf8/UTF-8/g", shell=True).decode("utf-8").split("\n")
        for line in locales.split("\n"):
            line = line.strip()
            if line == '' or line.startswith('#'):
                continue
            parts = line.split(" ")
            locale = parts[0].strip()
            lcharmap = None
            if len(parts) > 1:
                lcharmap = parts[1].strip()

            if locale not in installed:
                locale_code = locale.split(".")[0].strip()
                charmap = None
                if len(locale.split(".")) > 1:
                    charmap = locale.split(".")[1].strip()

                if "_" in locale_code:
                    split = locale_code.split("_")
                    if len(split) == 2:
                        language_code = split[0]

                        if language_code == "iw":
                            continue  # use 'he' instead

                        if language_code in self.languages:
                            language = self.languages[language_code]
                        else:
                            language = language_code

                        country_code = split[1].split('@')[0].lower()
                        if country_code in self.countries:
                            country = self.countries[country_code]
                        else:
                            country = country_code

                        if '@' in split[1]:
                            language_label = "%s (@%s), %s" % (language, split[1].split('@')[1].strip(), country)
                        else:
                            language_label = "%s, %s" % (language, country)
                        flag_path = FLAG_PATH % country_code
                else:
                    if locale_code in self.languages:
                        language_label = self.languages[locale_code]
                    else:
                        language_label = locale_code
                    flag_path = FLAG_PATH % locale_code

                flag_path = self.set_minority_language_flag_path(locale_code, flag_path)

                if lcharmap is not None:
                    language_label = "%s <small><span foreground='#3c3c3c'>%s</span></small>" % (language_label, lcharmap)

                iter = model.append()
                model.set_value(iter, 0, language_label)
                model.set_value(iter, 1, line)
                if os.path.exists(flag_path):
                    model.set_value(iter, 2, GdkPixbuf.Pixbuf.new_from_file_at_size(flag_path, -1, FLAG_SIZE))
                else:
                    model.set_value(iter, 2, GdkPixbuf.Pixbuf.new_from_file_at_size(FLAG_PATH % '_generic', -1, FLAG_SIZE))

        treeview = self.builder.get_object("treeview_language_list")
        treeview.set_model(model)
        treeview.set_search_column(0)
        self.treeview.connect("cursor-changed", self.select_language)

    def select_language(self, treeview, data=None):
        model = treeview.get_model()
        active = treeview.get_selection().get_selected_rows()
        if(len(active) > 0):
            active = active[1]
            if (len(active) > 0):
                active = active[0]
                if active is not None:
                    row = model[active]
                    language = row[1]
                    self.selected_language = language
                    self.builder.get_object("button_install").set_sensitive(True)

    def button_install_clicked(self, button):
        parts = self.selected_language.split(" ")
        locale = parts[0].strip()
        short_locale = locale.split(".")[0].strip()
        if len(parts) > 1:
            charmap = parts[1].strip()
            print("localedef -f %s -i %s %s" % (charmap, short_locale, locale))
            os.system("localedef -f %s -i %s %s" % (charmap, short_locale, locale))
        else:
            print("localedef -i %s %s" % (short_locale, locale))
            os.system("localedef -i %s %s" % (short_locale, locale))
        if os.path.exists("/var/lib/locales/supported.d"):
            os.system("localedef --list-archive | sed 's/utf8/UTF-8 UTF-8/g' > /var/lib/locales/supported.d/mintlocale")
        sys.exit(0)

if __name__ == "__main__":
    MintLocale()
    Gtk.main()

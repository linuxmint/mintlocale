#!/usr/bin/python3

import os
import gettext
import apt_pkg
import subprocess
import locale
import codecs
import mintcommon.aptdaemon

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

class LanguagePack:

    def __init__(self, category, language, dependency, package):
        self.category = category
        self.language = language
        self.dependency = dependency
        self.package = package

class MintLocale:

    ''' Create the UI '''

    def __init__(self):

        self.selected_language = None
        self.selected_language_packs = None

        self.language_packs = []
        with codecs.open("/usr/share/linuxmint/mintlocale/language_packs", 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                columns = line.split(":")
                if len(columns) == 4:
                    (category, language, dependency, package) = columns
                    if package.endswith("-"):
                        self.language_packs.append(LanguagePack(category, language, dependency, "%sLANG" % package))
                        self.language_packs.append(LanguagePack(category, language, dependency, "%sLANG-COUNTRY" % package))
                    else:
                        self.language_packs.append(LanguagePack(category, language, dependency, package))

        apt_pkg.init()
        self.cache = apt_pkg.Cache(None)
        self.cache_updated = False


        self.builder = Gtk.Builder()
        self.builder.set_translation_domain("mintlocale")
        self.builder.add_from_file('/usr/share/linuxmint/mintlocale/install_remove.ui')
        self.window = self.builder.get_object("main_window")
        self.window.set_icon_name("preferences-desktop-locale")
        self.builder.get_object("main_window").connect("destroy", Gtk.main_quit)

        self.treeview = self.builder.get_object("treeview_language_list")

        self.builder.get_object("main_window").set_title(_("Install / Remove Languages"))
        self.builder.get_object("main_window").set_icon_name("preferences-desktop-locale")
        self.builder.get_object("main_window").connect("destroy", Gtk.main_quit)
        self.builder.get_object("button_close").connect("clicked", Gtk.main_quit)
        self.builder.get_object("button_install").connect("clicked", self.button_install_clicked)
        self.builder.get_object("button_add").connect("clicked", self.button_add_clicked)
        self.builder.get_object("button_remove").connect("clicked", self.button_remove_clicked)

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

        ren = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Packs", ren)
        column.add_attribute(ren, "markup", 3)
        ren.set_property('xpad', 10)
        self.treeview.append_column(column)

        self.build_lang_list()

        self.apt = mintcommon.aptdaemon.APT(self.window)

    def split_locale(self, locale_code):
        if "_" in locale_code:
            split = locale_code.split("_")
            language_code = split[0]
            if language_code in self.languages:
                language = self.languages[language_code]
            else:
                language = language_code

            country_code = split[1].lower().split('@')[0].strip()
            if country_code in self.countries:
                country = self.countries[country_code]
            else:
                country = country_code

            if '@' in split[1]:
                language_label = "%s (@%s), %s" % (language, split[1].split('@')[1].strip(), country)
            else:
                language_label = "%s, %s" % (language, country)
        else:
            if locale_code in self.languages:
                language_label = self.languages[locale_code]
            else:
                language_label = locale_code
            language_code = locale_code
            country_code = ""

        return (language_code, country_code, language_label)

    def build_lang_list(self):
        self.cache = apt_pkg.Cache(None)

        self.builder.get_object('button_install').set_sensitive(False)
        self.builder.get_object('button_remove').set_sensitive(False)

        model = Gtk.ListStore(str, str, GdkPixbuf.Pixbuf, str, bool, object)  # label, locale, flag, packs_label, packs_installed, list_of_missing_packs
        model.set_sort_column_id(0, Gtk.SortType.ASCENDING)

        # Load countries into memory
        self.countries = {}
        with codecs.open('/usr/share/linuxmint/mintlocale/countries', "r", encoding="utf-8") as file:
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

        locales = subprocess.check_output("localedef --list-archive", shell=True)
        locales = locales.decode('utf-8').strip()
        for line in locales.split("\n"):
            line = line.replace("utf8", "UTF-8").strip()

            locale_code = line.split(".")[0].strip()
            charmap = None
            if len(line.split(".")) > 1:
                charmap = line.split(".")[1].strip()

            language_code, country_code, language_label = self.split_locale(locale_code)
            if country_code == "":
                flag_path = FLAG_PATH % locale_code
            else:
                flag_path = FLAG_PATH % country_code

            # Check for minority languages. Get tje language code from the locale_code.
            # For example, Basque's locale code can be eu or eu_es or eu_fr, Welsh's cy or cy_gb...
            if language_code == 'ca':
                flag_path = FLAG_PATH % '_catalonia'
            elif language_code == 'cy':
                flag_path = FLAG_PATH % '_wales'
            elif language_code == 'eu':
                flag_path = FLAG_PATH % '_basque'
            elif language_code == 'gl':
                flag_path = FLAG_PATH % '_galicia'

            if charmap is not None:
                language_label = "%s <small><span foreground='#3c3c3c'>%s</span></small>" % (language_label, charmap)

            # Check if the language packs are installed
            missing_packs = []
            missing_pack_names = []
            for language_pack in self.language_packs:
                if language_pack.language == "" or language_pack.language == language_code:
                    pkgname = language_pack.package.replace("LANG", language_code).replace("COUNTRY", country_code)
                    depname = language_pack.dependency
                    if pkgname in self.cache:
                        pkg = self.cache[pkgname]
                        if (pkg.has_versions and pkg.current_state != apt_pkg.CURSTATE_INSTALLED):
                            if depname != "":
                                if depname in self.cache and self.cache[depname].current_state == apt_pkg.CURSTATE_INSTALLED:
                                    if pkgname not in missing_pack_names:
                                        missing_packs.append(pkg)
                                        missing_pack_names.append(pkgname)
                            else:
                                if pkgname not in missing_pack_names:
                                    missing_packs.append(pkg)
                                    missing_pack_names.append(pkgname)

            iter = model.append()
            model.set_value(iter, 0, language_label)
            model.set_value(iter, 1, line)
            if len(missing_pack_names) > 0:
                model.set_value(iter, 3, "<small><span fgcolor='#a04848'>%s</span></small>" % _("Some language packs are missing"))
                model.set_value(iter, 4, False)
                model.set_value(iter, 5, missing_pack_names)
            else:
                model.set_value(iter, 3, "<small><span fgcolor='#4ba048'>%s</span></small>" % _("Fully installed"))
                model.set_value(iter, 4, True)
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
                    langpacks_installed = row[4]
                    self.selected_language = language
                    self.selected_language_packs = row[5]
                    self.builder.get_object("button_remove").set_sensitive(True)
                    self.builder.get_object("button_install").set_sensitive(not langpacks_installed)

    def button_install_clicked(self, button):
        if self.selected_language_packs is not None:
            if self.cache_updated:
                self.apt.set_finished_callback(self.on_install_finished)
                self.apt.set_cancelled_callback(self.on_install_finished)
                self.apt.install_packages(self.selected_language_packs)
            else:
                self.apt.set_finished_callback(self.on_update_finished)
                self.apt.update_cache()

    def on_update_finished(self, transaction=None, exit_state=None):
        self.cache_updated = True
        self.apt.set_finished_callback(self.on_install_finished)
        self.apt.set_cancelled_callback(self.on_install_finished)
        self.apt.install_packages(self.selected_language_packs)

    def on_install_finished(self, transaction=None, exit_state=None):
        self.build_lang_list()

    def button_add_clicked(self, button):
        os.system("/usr/lib/linuxmint/mintlocale/add.py")
        self.build_lang_list()

    def button_remove_clicked(self, button):
        locale = self.selected_language.replace("UTF-8", "utf8")
        os.system("localedef --delete-from-archive %s" % locale)
        # If there are no more locales using the language, remove the language packs
        (language_code, country_code, language_label) = self.split_locale(locale)
        num_locales = subprocess.check_output("localedef --list-archive | grep %s_ | wc -l" % language_code, shell=True)
        num_locales = num_locales.decode('utf-8').strip()
        # Check if the language packs are installed
        if num_locales == "0":
            installed_packs = []
            for prefix in ["language-pack", "language-pack-gnome"]:
                for pkgname in ["%s-%s" % (prefix, language_code), "%s-%s-%s" % (prefix, language_code, country_code)]:
                    if pkgname in self.cache:
                        pkg = self.cache[pkgname]
                        if (pkg.has_versions and pkg.current_state == apt_pkg.CURSTATE_INSTALLED):
                            installed_packs.append(pkgname)
                            print(pkgname)

            if len(installed_packs) > 0:
                self.apt.set_finished_callback(self.on_install_finished)
                self.apt.remove_packages(installed_packs)

        self.build_lang_list()

if __name__ == "__main__":
    MintLocale()
    Gtk.main()

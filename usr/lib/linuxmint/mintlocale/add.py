#!/usr/bin/python3

import os
import subprocess
import sys
import gettext
import locale

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf

import localegen
import localeinfo

# i18n
APP = 'mintlocale'
LOCALE_DIR = "/usr/share/linuxmint/locale"
locale.bindtextdomain(APP, LOCALE_DIR)
gettext.bindtextdomain(APP, LOCALE_DIR)
gettext.textdomain(APP)
_ = gettext.gettext

FLAG_SIZE = 22

class MintLocale:

    ''' Create the UI '''

    def __init__(self):

        self.selected_language = None
        self.locale_info = localeinfo.LocaleInfo()

        self.builder = Gtk.Builder()
        self.builder.set_translation_domain("mintlocale")
        self.builder.add_from_file('/usr/share/linuxmint/mintlocale/add.ui')
        self.window = self.builder.get_object("main_window")
        self.scale = self.window.get_scale_factor()

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
        column.set_cell_data_func(ren, self.data_func_surface)
        ren.set_property('ypad', 5)
        ren.set_property('xpad', 10)
        self.treeview.append_column(column)

        ren = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Languages", ren)
        column.add_attribute(ren, "markup", 0)
        self.treeview.append_column(column)

        self.build_lang_list()

    def data_func_surface(self, column, cell, model, iter_, *args):
        pixbuf = model.get_value(iter_, 2)
        surface = Gdk.cairo_surface_create_from_pixbuf(pixbuf, self.scale)
        cell.set_property("surface", surface)

    def build_lang_list(self):
        self.builder.get_object('button_install').set_sensitive(False)

        model = Gtk.ListStore(str, str, GdkPixbuf.Pixbuf)  # label, locale, flag
        model.set_sort_column_id(0, Gtk.SortType.ASCENDING)

        if os.path.exists("/usr/share/i18n/SUPPORTED"):
            with open("/usr/share/i18n/SUPPORTED", "r", encoding="utf-8") as file:
                locales = file.read()
        else:
            locales = u""

        installed = subprocess.check_output("localedef --list-archive | sed s/utf8/UTF-8/g", shell=True).decode("utf-8").split("\n")
        for line in locales.split("\n"):
            line = line.strip()
            if line == '' or line.startswith('#'):
                continue
            # Only allow UTF-8 locales
            if "UTF-8" not in line:
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

                language_code, country_code, language_label = self.locale_info.split_locale(locale_code)
                if language_code == "iw":
                    continue  # use 'he' instead
                flag_path = self.locale_info.get_flag_path(language_code, country_code)

                if lcharmap is not None and lcharmap != "UTF-8":
                    language_label = "%s <small><span foreground='#3c3c3c'>%s</span></small>" % (language_label, lcharmap)

                iter = model.append()
                model.set_value(iter, 0, language_label)
                model.set_value(iter, 1, line)
                model.set_value(iter, 2, GdkPixbuf.Pixbuf.new_from_file_at_size(flag_path, -1, FLAG_SIZE * self.scale))

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
        print("Installing locale %s" % self.selected_language)
        localegen.install_locale(self.selected_language)
        sys.exit(0)

if __name__ == "__main__":
    MintLocale()
    Gtk.main()

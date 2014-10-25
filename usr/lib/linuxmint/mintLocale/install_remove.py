#!/usr/bin/env python

import gi
from gi.repository import Gtk, GdkPixbuf, Gdk, GObject, Gio, GdkX11

try:
    import os
    import commands
    import sys
    import string
    import gettext
    import apt_pkg
    from subprocess import Popen
    import tempfile
    import locale
except Exception, detail:
    print detail
    sys.exit(1)

# i18n
APP = 'mintlocale'
LOCALE_DIR = "/usr/share/linuxmint/locale"
locale.bindtextdomain(APP, LOCALE_DIR)
gettext.bindtextdomain(APP, LOCALE_DIR)
gettext.textdomain(APP)
_ = gettext.gettext

class MintLocale:
   
    ''' Create the UI '''
    def __init__(self):

        self.selected_language = None
        self.selected_language_packs = None
        codename = commands.getoutput("lsb_release -cs")
        if codename == "debian":
            self.pack_prefixes = ["firefox-l10n-", "thunderbird-l10n-", "libreoffice-l10n-", "hunspell-"]
        else:
            self.pack_prefixes = ["language-pack-", "language-pack-gnome-", "firefox-locale-", "thunderbird-locale-", "libreoffice-l10n-", "hunspell-"]
        
        apt_pkg.init()        

        self.builder = Gtk.Builder()
        self.builder.set_translation_domain("mintlocale")
        self.builder.add_from_file('/usr/lib/linuxmint/mintLocale/install_remove.ui')
        self.window = self.builder.get_object( "main_window" )
               
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
        
    def build_lang_list(self):
        self.cache = apt_pkg.Cache(None)

        self.builder.get_object('button_install').set_sensitive(False)
        self.builder.get_object('button_remove').set_sensitive(False)

        model = Gtk.ListStore(str, str, GdkPixbuf.Pixbuf, str, bool, object) # label, locale, flag, packs_label, packs_installed, list_of_missing_packs
        model.set_sort_column_id(0, Gtk.SortType.ASCENDING)

        #Load countries into memory
        self.countries = {}
        file = open('/usr/lib/linuxmint/mintLocale/countries', "r")
        for line in file:
            line = line.strip()
            split = line.split("=")
            if len(split) == 2:
                self.countries[split[0]] = split[1]
        file.close()

        #Load languages into memory
        self.languages = {}
        file = open('/usr/lib/linuxmint/mintLocale/languages', "r")
        for line in file:
            line = line.strip()
            split = line.split("=")
            if len(split) == 2:
                self.languages[split[0]] = split[1]
        file.close()
                
        locales = commands.getoutput("localedef --list-archive")
        for line in locales.split("\n"):
            line = line.replace("utf8", "UTF-8")            
            locale_code = line.split(".")[0].strip()
            charmap = None
            if len(line.split(".")) > 1:
                charmap = line.split(".")[1].strip()

            if "_" in locale_code:
                split = locale_code.split("_")
                if len(split) == 2:
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

                    flag_path = '/usr/share/linuxmint/mintLocale/flags/16/' + country_code + '.png'
            else:
                if locale_code in self.languages:
                    language_label = self.languages[locale_code]
                else:
                    language_label = locale_code                    
                flag_path = '/usr/share/linuxmint/mintLocale/flags/16/languages/%s.png' % locale_code
                language_code = locale_code

            if charmap is not None:
                language_label = "%s <small><span foreground='#3c3c3c'>%s</span></small>" % (language_label, charmap)

            # Check if the language packs are installed
            missing_packs = []
            for pkgname in self.pack_prefixes:
                pkgname = "%s%s" % (pkgname, language_code)
                if pkgname in self.cache:
                    pkg = self.cache[pkgname]
                    if (pkg.has_versions and pkg.current_state != apt_pkg.CURSTATE_INSTALLED):
                        missing_packs.append(pkg)
            
            iter = model.append()
            model.set_value(iter, 0, language_label)
            model.set_value(iter, 1, line)
            if len(missing_packs) > 0:
                model.set_value(iter, 3, "<small><span fgcolor='#a04848'>%s</span></small>" % _("Some language packs are missing"))
                model.set_value(iter, 4, False)
                model.set_value(iter, 5, missing_packs)
            else:
                model.set_value(iter, 3, "<small><span fgcolor='#4ba048'>%s</span></small>" % _("Fully installed"))
                model.set_value(iter, 4, True)
            if os.path.exists(flag_path):
                model.set_value(iter, 2, GdkPixbuf.Pixbuf.new_from_file(flag_path))
            else:
                model.set_value(iter, 2, GdkPixbuf.Pixbuf.new_from_file('/usr/share/linuxmint/mintLocale/flags/16/generic.png'))
                             
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
    
    def button_install_clicked (self, button):
        if self.selected_language_packs is not None:            
            cmd = ["/usr/sbin/synaptic", "--hide-main-window", "--non-interactive", "--parent-window-id", "%s" % self.builder.get_object("main_window").get_window().get_xid()]
            cmd.append("-o")
            cmd.append("Synaptic::closeZvt=true")
            cmd.append("--progress-str")
            cmd.append("\"" + _("Please wait, this can take some time") + "\"")
            cmd.append("--finish-str")
            cmd.append("\"" + _("Installation is complete") + "\"")
            f = tempfile.NamedTemporaryFile()
            for pkg in self.selected_language_packs:
                f.write("%s\tinstall\n" % pkg.name)
            cmd.append("--set-selections-file")
            cmd.append("%s" % f.name)
            f.flush()
            comnd = Popen(' '.join(cmd), shell=True)
            returnCode = comnd.wait()            
            f.close()
        self.build_lang_list()

    def button_add_clicked (self, button):
        os.system("/usr/lib/linuxmint/mintLocale/add.py")
        self.build_lang_list()

    def button_remove_clicked (self, button):
        locale = self.selected_language.replace("UTF-8", "utf8")
        language_code = locale.split("_")[0]
        os.system("localedef --delete-from-archive %s" % locale)
        # If there are no more locales using the language, remove the language packs
        num_locales = commands.getoutput("localedef --list-archive | grep %s_ | wc -l" % language_code)
        # Check if the language packs are installed
        if num_locales == "0":
            installed_packs = []
            for pkgname in self.pack_prefixes:
                pkgname = "%s%s" % (pkgname, language_code)
                if pkgname in self.cache:
                    pkg = self.cache[pkgname]
                    if (pkg.has_versions and pkg.current_state == apt_pkg.CURSTATE_INSTALLED):
                        installed_packs.append(pkg)
        
            if len(installed_packs) > 0:
                cmd = ["/usr/sbin/synaptic", "--hide-main-window", "--non-interactive", "--parent-window-id", "%s" % self.builder.get_object("main_window").get_window().get_xid()]
                cmd.append("-o")
                cmd.append("Synaptic::closeZvt=true")
                cmd.append("--progress-str")
                cmd.append("\"" + _("Please wait, this can take some time") + "\"")
                cmd.append("--finish-str")
                cmd.append("\"" + _("The related language packs were removed") + "\"")
                f = tempfile.NamedTemporaryFile()
                for pkg in installed_packs:
                    f.write("%s\tdeinstall\n" % pkg.name)
                cmd.append("--set-selections-file")
                cmd.append("%s" % f.name)
                f.flush()
                comnd = Popen(' '.join(cmd), shell=True)
                returnCode = comnd.wait()            
                f.close()

        self.build_lang_list()

if __name__ == "__main__":
    MintLocale()
    Gtk.main()

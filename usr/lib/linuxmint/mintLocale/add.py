#!/usr/bin/env python

import gi
from gi.repository import Gtk, GdkPixbuf, Gdk, GObject, Gio

try:
    import os
    import commands
    import sys
    import string
    import gettext    
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
        
        self.builder = Gtk.Builder()
        self.builder.set_translation_domain("mintlocale")
        self.builder.add_from_file('/usr/lib/linuxmint/mintLocale/add.ui')
        self.window = self.builder.get_object( "main_window" )
               
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
        column.add_attribute(ren, "text", 0)
        self.treeview.append_column(column)
        
        self.build_lang_list()
        
    def build_lang_list(self):
        self.builder.get_object('button_install').set_sensitive(False)

        model = Gtk.ListStore(str, str, GdkPixbuf.Pixbuf) # label, locale, flag
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
                
        locales = commands.getoutput("cat /usr/share/i18n/SUPPORTED | awk {'print $1;'} | grep UTF-8")
        installed = commands.getoutput("localedef --list-archive | grep utf8 | sed s/utf8/UTF-8/g").split("\n")
        for line in locales.split("\n"):            
            if line not in installed:
                locale_code = line.replace("UTF-8", "")
                locale_code = locale_code.replace(".", "")
                locale_code = locale_code.strip()
                
                if "_" in locale_code:
                    split = locale_code.split("_")
                    if len(split) == 2:
                        language_code = split[0]

                        if language_code == "iw":
                            continue # use 'he' instead

                        if language_code in self.languages:
                            language = self.languages[language_code]
                        else:
                            language = language_code

                        country_code = split[1].lower()
                        if country_code in self.countries:
                            country = self.countries[country_code]
                        else:
                            country = country_code

                        language_label = "%s, %s" % (language, country)
                        flag_path = '/usr/share/linuxmint/mintLocale/flags/16/' + country_code + '.png'
                else:                                        
                    if locale_code in self.languages:
                        language_label = self.languages[locale_code]
                    else:
                        language_label = locale_code
                    flag_path = '/usr/share/linuxmint/mintLocale/flags/16/languages/%s.png' % locale_code
                    
                                            
                iter = model.append()
                model.set_value(iter, 0, language_label)
                model.set_value(iter, 1, line)                        
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
                    self.selected_language = language
                    self.builder.get_object("button_install").set_sensitive(True)
    
    def button_install_clicked (self, button):
        locale = self.selected_language.replace(".UTF-8", "")
        os.system("localedef -f UTF-8 -i %s %s.UTF-8" % (locale, locale))
        if os.path.exists("/var/lib/locales/supported.d"):
        	os.system("localedef --list-archive | grep utf8 | sed 's/utf8/UTF-8 UTF-8/g' > /var/lib/locales/supported.d/mintlocale")
        sys.exit(0)
    
if __name__ == "__main__":
    MintLocale()
    Gtk.main()

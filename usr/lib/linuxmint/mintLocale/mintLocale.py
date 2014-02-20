#!/usr/bin/env python

import gi
from gi.repository import Gtk, GdkPixbuf, Gdk, GObject, Gio, AccountsService, GLib

try:
    import os
    import commands
    import sys
    import string
    import gettext 
    import ConfigParser
    import grp
except Exception, detail:
    print detail
    sys.exit(1)

# i18n
gettext.install("mintlocale", "/usr/share/linuxmint/locale")

# i18n for menu item
menuName = _("Languages")
menuComment = _("Language settings")

class MintLocale:
   
    ''' Create the UI '''
    def __init__(self):

        # load our glade ui file in
        self.builder = Gtk.Builder()
        self.builder.add_from_file('/usr/lib/linuxmint/mintLocale/mintLocale.ui')
        self.window = self.builder.get_object( "main_window" )
               
        self.builder.get_object("main_window").connect("destroy", Gtk.main_quit)

        self.treeview = self.builder.get_object("treeview_language_list")
                              
        # set up larger components.
        self.builder.get_object("main_window").set_title(_("Language Settings"))
        self.builder.get_object("main_window").connect("destroy", Gtk.main_quit)
        self.builder.get_object("button_close").connect("clicked", Gtk.main_quit)
        self.builder.get_object("button_system_language").connect("clicked", self.button_system_language_clicked)
        self.builder.get_object("button_install_remove").connect("clicked", self.button_install_remove_clicked)

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
        
        self.pam_environment_path = os.path.join(GLib.get_home_dir(), ".pam_environment")
        self.dmrc_path = os.path.join(GLib.get_home_dir(), ".dmrc")
        self.dmrc = ConfigParser.ConfigParser()
        self.dmrc.read(self.dmrc_path)
        if not self.dmrc.has_section('Desktop'):
            self.dmrc.add_section('Desktop')

        current_user = GLib.get_user_name()        

        self.current_language = None
        dmrc_language = None
        env_language = os.environ['LANG']
        
        if self.dmrc.has_option('Desktop', 'Language'):
            dmrc_language = self.dmrc.get('Desktop', 'Language')
        
        if dmrc_language is not None:
            self.current_language = dmrc_language
        else:
            self.current_language = env_language

        print "User language in .dmrc: %s" % dmrc_language
        print "User language in $LANG: %s" % env_language
        print "Current language: %s" % self.current_language

        self.build_lang_list()
        self.set_system_locale()
        self.set_num_installed()

        self.accountService = AccountsService.UserManager.get_default().get_user(current_user)
        self.accountService.connect('notify::is-loaded', self.accountservice_ready)
        self.accountService.connect('changed::', self.accountservice_changed)

        groups = grp.getgrall()
        for group in groups:
            (name, pw, gid, mem) = group
            if name in ("adm", "sudo"):
                for user in mem:
                    if current_user == user:
                        self.builder.get_object("separator").show()
                        self.builder.get_object("button_system_language").show()
                        self.builder.get_object("button_install_remove").show()

    def button_system_language_clicked (self, button):
        os.system("gksu set-default-locale '%s'" % self.current_language)
        self.set_system_locale()

    def button_install_remove_clicked (self, button):
        os.system("gksu add-remove-locales")
        self.build_lang_list()
        self.set_system_locale()
        self.set_num_installed()

    def set_system_locale(self):
        self.builder.get_object("image_system_language").set_from_file('/usr/lib/linuxmint/mintLocale/flags/16/generic.png')
        self.builder.get_object("label_system_language").set_text(_("No locale defined"))

        # Get system locale
        if os.path.exists("/etc/default/locale"):
            vars = dict()
            with open("/etc/default/locale") as f:
                for line in f:
                    eq_index = line.find('=')
                    var_name = line[:eq_index].strip()
                    value = line[eq_index + 1:].strip()
                    vars[var_name] = value
            if "LANG" in vars:
                locale = vars['LANG'].replace('"', '').replace("'", "")
                locale = locale.replace("utf8", "UTF-8")
                locale = locale.replace("UTF-8", "")
                locale = locale.replace(".", "")
                locale = locale.strip()
                if "_" in locale:
                    split = locale.split("_")
                    if len(split) == 2:
                        language_code = split[0]
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
                        flag_path = '/usr/lib/linuxmint/mintLocale/flags/16/' + country_code + '.png'
                else:
                    if locale in self.languages:
                        language_label = self.languages[locale]
                    else:
                        language_label = locale
                    flag_path = '/usr/lib/linuxmint/mintLocale/flags/16/languages/%s.png' % locale                    
                
                self.builder.get_object("label_system_language").set_text(language_label)                
                        
                if os.path.exists(flag_path):
                    self.builder.get_object("image_system_language").set_from_file(flag_path)
                else:
                    self.builder.get_object("image_system_language").set_from_file('/usr/lib/linuxmint/mintLocale/flags/16/generic.png')

    def set_num_installed (self):
        num_installed = commands.getoutput("localedef --list-archive | grep utf8 | wc -l")
        self.builder.get_object("label_num_languages_installed").set_text(num_installed)

    def accountservice_ready(self, user, param):
        self.builder.get_object("main_window").show()
        self.treeview.connect("cursor-changed", self.select_language)

    def accountservice_changed(self, user):        
        print "AccountsService language is: '%s'" % user.get_language()

    def build_lang_list(self):
        model = Gtk.ListStore(str,str,GdkPixbuf.Pixbuf, str)
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
        
        cur_index = -1 # find the locale :P
        set_index = None
        locales = commands.getoutput("localedef --list-archive")
        for line in locales.split("\n"):
            line = line.replace("utf8", "UTF-8")
            if "UTF-8" not in line:
                continue            
            cur_index += 1        
            locale_code = line.replace("UTF-8", "")
            locale_code = locale_code.replace(".", "")
            locale_code = locale_code.strip()

            if "_" in locale_code:
                split = locale_code.split("_")
                if len(split) == 2:
                    language_code = split[0]

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
                    flag_path = '/usr/lib/linuxmint/mintLocale/flags/16/' + country_code + '.png'
            else:                                        
                if locale_code in self.languages:
                    language_label = self.languages[locale_code]
                else:
                    language_label = locale_code
                flag_path = '/usr/lib/linuxmint/mintLocale/flags/16/languages/%s.png' % locale_code

            iter = model.append()
            model.set_value(iter, 0, language_label)
            model.set_value(iter, 1, line)
            model.set_value(iter, 3, "<small><span fgcolor='#9c9c9c'>%s</span></small>" % line)            
            if os.path.exists(flag_path):
                model.set_value(iter, 2, GdkPixbuf.Pixbuf.new_from_file(flag_path))
            else:                
                model.set_value(iter, 2, GdkPixbuf.Pixbuf.new_from_file('/usr/lib/linuxmint/mintLocale/flags/16/generic.png'))
            
            if (line == self.current_language):                        
                if (set_index is None):
                    set_index = iter

        treeview = self.builder.get_object("treeview_language_list")
        treeview.set_model(model)
        if set_index is not None:
            column = treeview.get_column(0)
            path = model.get_path(set_index)
            treeview.set_cursor(path)
            treeview.scroll_to_cell(path, column=column)
            self.builder.get_object("button_system_language").set_sensitive(True)
        treeview.set_search_column(0)    

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
                    print "Setting language to '%s'" % language

                    # Set it in Accounts Service
                    try:
                        self.accountService.set_language(language)
                    except:
                        pass

                    # Set it in .dmrc
                    self.dmrc.set('Desktop','Language', language)
                    with open(self.dmrc_path, 'wb') as configfile:
                        self.dmrc.write(configfile)

                    # Set it in .pam_environment
                    if os.path.exists(self.pam_environment_path):                        
                        for lc_variable in ['LANGUAGE', 'LANG']:
                             os.system("sed -i '/^%s=.*/d' %s" % (lc_variable, self.pam_environment_path))
                        for lc_variable in ['LC_NUMERIC', 'LC_TIME', 'LC_MONETARY', 'LC_PAPER', 'LC_NAME', 'LC_ADDRESS', 'LC_TELEPHONE', 'LC_MEASUREMENT', 'LC_IDENTIFICATION']:
                             os.system("sed -i 's/^%s=.*/%s=%s/g' %s" % (lc_variable, lc_variable, language, self.pam_environment_path))
                    
                    self.current_language = language
                    self.builder.get_object("button_system_language").set_sensitive(True)
    
if __name__ == "__main__":
    MintLocale()
    Gtk.main()

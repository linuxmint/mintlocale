#!/usr/bin/python3

import os
import gettext
import grp
import locale
import subprocess
import codecs

try:
    import configparser
except ImportError as err:
    import ConfigParser as configparser

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('AccountsService', '1.0')
gi.require_version('XApp', '1.0')
from gi.repository import Gtk, AccountsService, GLib, GdkPixbuf, XApp


# Used to detect Debian derivatives (we don't want to show APT features in other distros)
IS_DEBIAN = os.path.exists("/etc/debian_version")

if IS_DEBIAN:
    import apt

# i18n
APP = 'mintlocale'
LOCALE_DIR = "/usr/share/linuxmint/locale"
locale.bindtextdomain(APP, LOCALE_DIR)
gettext.bindtextdomain(APP, LOCALE_DIR)
gettext.textdomain(APP)
_ = gettext.gettext

FLAG_PATH = "/usr/share/iso-flag-png/%s.png"
FLAG_SIZE = 22
BUTTON_FLAG_SIZE = 22

def list_header_func(row, before, user_data):
    if before and not row.get_header():
        row.set_header(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

class Locale():

    def __init__(self, id, name):
        self.id = id
        self.name = name

class PictureChooserButton (Gtk.Button):

    def __init__(self, num_cols=4, button_picture_size=None, menu_pictures_size=None, has_button_label=False):
        super(PictureChooserButton, self).__init__()
        self.num_cols = num_cols
        self.button_picture_size = button_picture_size
        self.menu_pictures_size = menu_pictures_size
        self.row = 0
        self.col = 0
        self.menu = Gtk.Menu()
        self.button_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.button_image = Gtk.Image()
        self.button_box.add(self.button_image)

        if has_button_label:
            self.button_label = Gtk.Label()
            self.button_box.add(self.button_label)

        self.add(self.button_box)
        self.connect("button-release-event", self._on_button_clicked)
        self.progress = 0.0

        context = self.get_style_context()
        context.add_class("gtkstyle-fallback")

        self.connect_after("draw", self.on_draw)

    def on_draw(self, widget, cr, data=None):
        if self.progress == 0:
            return False

        box = widget.get_allocation()

        context = widget.get_style_context()
        c = context.get_background_color(Gtk.StateFlags.SELECTED)

        max_length = box.width * .6
        start = (box.width - max_length) / 2
        y = box.height - 5

        cr.save()

        cr.set_source_rgba(c.red, c.green, c.blue, c.alpha)
        cr.set_line_width(3)
        cr.set_line_cap(1)
        cr.move_to(start, y)
        cr.line_to(start + (self.progress * max_length), y)
        cr.stroke()

        cr.restore()
        return False

    def increment_loading_progress(self, inc):
        progress = self.progress + inc
        self.progress = min(1.0, progress)
        self.queue_draw()

    def reset_loading_progress(self):
        self.progress = 0.0
        self.queue_draw()

    def set_picture_from_file(self, path):
        if self.menu_pictures_size is not None:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(path, -1, self.menu_pictures_size)
        else:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(path, -1, FLAG_SIZE)
        self.button_image.set_from_pixbuf(pixbuf)

    def set_button_label(self, label):
        self.button_label.set_markup(label)

    def popup_menu_below_button(self, menu, *args):
        # Done this way for compatibility across Gtk versions
        # Mint 17.x   =>   "widget" will be arg 2
        # Mint 18.x   =>   "widget" will be arg 4
        widget = args[-1]

        window = widget.get_window()
        screen = window.get_screen()
        monitor = screen.get_monitor_at_window(window)

        warea = screen.get_monitor_workarea(monitor)
        wrect = widget.get_allocation()
        mrect = menu.get_allocation()

        unused_var, window_x, window_y = window.get_origin()

        # Position left edge of the menu with the right edge of the button
        x = window_x + wrect.x + wrect.width
        # Center the menu vertically with respect to the monitor
        y = warea.y + (warea.height / 2) - (mrect.height / 2)

        # Now, check if we're still touching the button - we want the right edge
        # of the button always 100% touching the menu

        if y > (window_y + wrect.y):
            y = y - (y - (window_y + wrect.y))
        elif (y + mrect.height) < (window_y + wrect.y + wrect.height):
            y = y + ((window_y + wrect.y + wrect.height) - (y + mrect.height))

        push_in = True  # push_in is True so all menu is always inside screen
        return (x, y, push_in)

    def _on_button_clicked(self, widget, event):
        if event.button == 1:
            self.menu.show_all()
            self.menu.popup(None, None, self.popup_menu_below_button, self, event.button, event.time)

    def _on_picture_selected(self, menuitem, path, callback, id=None):
        if id is not None:
            result = callback(path, id)
        else:
            result = callback(path)

        if result:
            self.set_picture_from_file(path)

    def clear_menu(self):
        menu = self.menu
        self.menu = Gtk.Menu()
        self.row = 0
        self.col = 0
        menu.destroy()

    def add_picture(self, path, callback, title=None, id=None):
        if os.path.exists(path):
            if self.button_picture_size is None:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(path, -1, FLAG_SIZE)
            else:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(path, -1, self.button_picture_size)
            image = Gtk.Image.new_from_pixbuf(pixbuf)
            menuitem = Gtk.MenuItem()
            if title is not None:
                vbox = Gtk.VBox()
                vbox.pack_start(image, False, False, 2)
                label = Gtk.Label()
                label.set_markup(title)
                vbox.pack_start(label, False, False, 2)
                menuitem.add(vbox)
            else:
                menuitem.add(image)
            if id is not None:
                menuitem.connect('activate', self._on_picture_selected, path, callback, id)
            else:
                menuitem.connect('activate', self._on_picture_selected, path, callback)
            self.menu.attach(menuitem, self.col, self.col + 1, self.row, self.row + 1)
            self.col = (self.col + 1) % self.num_cols
            if (self.col == 0):
                self.row = self.row + 1

    def add_separator(self):
        self.row = self.row + 1
        self.menu.attach(Gtk.SeparatorMenuItem(), 0, self.num_cols, self.row, self.row + 1)

    def add_menuitem(self, menuitem):
        self.row = self.row + 1
        self.menu.attach(menuitem, 0, self.num_cols, self.row, self.row + 1)


class SettingsPage(Gtk.Box):

    def __init__(self):
        Gtk.Box.__init__(self)
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.set_spacing(15)
        self.set_margin_left(80)
        self.set_margin_right(80)
        self.set_margin_top(15)
        self.set_margin_bottom(15)

    def add_section(self):
        section = SettingsBox()
        self.pack_start(section, False, False, 0)

        return section


class SettingsBox(Gtk.Frame):

    def __init__(self):
        Gtk.Frame.__init__(self)
        self.set_shadow_type(Gtk.ShadowType.IN)
        frame_style = self.get_style_context()
        frame_style.add_class("view")
        self.size_group = Gtk.SizeGroup()
        self.size_group.set_mode(Gtk.SizeGroupMode.VERTICAL)

        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(self.box)

        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.list_box.set_header_func(list_header_func, None)
        self.box.add(self.list_box)

    def add_row(self, row):
        self.list_box.add(row)


class SettingsRow(Gtk.ListBoxRow):

    def __init__(self, label, main_widget, alternative_widget=None):

        self.main_widget = main_widget
        self.alternative_widget = alternative_widget
        self.label = label
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack.set_transition_duration(1000)

        self.stack.add_named(main_widget, "main_widget")
        if alternative_widget is not None:
            self.stack.add_named(self.alternative_widget, "alternative_widget")

        Gtk.ListBoxRow.__init__(self)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hbox.set_border_width(5)
        hbox.set_margin_left(20)
        hbox.set_margin_right(20)
        self.add(hbox)

        grid = Gtk.Grid()
        grid.set_column_spacing(15)
        hbox.pack_start(grid, True, True, 0)

        self.description_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.description_box.props.hexpand = True
        self.description_box.props.halign = Gtk.Align.START
        self.description_box.props.valign = Gtk.Align.CENTER
        self.label.props.xalign = 0.0
        self.description_box.add(self.label)

        grid.attach(self.description_box, 0, 0, 1, 1)
        grid.attach_next_to(self.stack, self.description_box, Gtk.PositionType.RIGHT, 1, 1)

    def show_alternative_widget(self):
        if self.alternative_widget is not None:
            self.stack.set_visible_child(self.alternative_widget)


class MintLocale:

    ''' Create the UI '''

    def __init__(self):

        # Determine path to system locale-config
        self.locale_path=''

        if os.path.exists('/etc/default/locale'):
            self.locale_path='/etc/default/locale'
        else:
            self.locale_path='/etc/locale.conf'

        # Prepare the APT cache
        if IS_DEBIAN:
            self.cache = apt.Cache()
        self.cache_updated = False

        # load our glade ui file in
        self.builder = Gtk.Builder()
        self.builder.set_translation_domain("mintlocale")
        self.builder.add_from_file('/usr/share/linuxmint/mintlocale/mintlocale.ui')

        self.window = self.builder.get_object("main_window")
        self.window.set_title(_("Language Settings"))
        self.window.connect("destroy", Gtk.main_quit)
        XApp.set_window_icon_name(self.window, "preferences-desktop-locale")

        self.toolbar = Gtk.Toolbar()
        self.toolbar.get_style_context().add_class("primary-toolbar")
        self.builder.get_object("box1").pack_start(self.toolbar, False, False, 0)


        size_group = Gtk.SizeGroup.new(Gtk.SizeGroupMode.HORIZONTAL)

        self.locale_button = PictureChooserButton(num_cols=2, button_picture_size=BUTTON_FLAG_SIZE, has_button_label=True)
        size_group.add_widget(self.locale_button)
        self.region_button = PictureChooserButton(num_cols=2, button_picture_size=BUTTON_FLAG_SIZE, has_button_label=True)
        size_group.add_widget(self.region_button)

        self.locale_system_wide_button = Gtk.Button()
        self.locale_system_wide_button.set_label(_("Apply System-Wide"))
        self.locale_system_wide_button.connect("clicked", self.button_system_language_clicked)
        size_group.add_widget(self.locale_system_wide_button)

        self.locale_install_button = Gtk.Button()
        self.locale_install_button.set_label(_("Install / Remove Languages..."))
        self.locale_install_button.connect("clicked", self.button_install_remove_clicked)
        size_group.add_widget(self.locale_install_button)

        self.system_label = Gtk.Label()
        self.install_label = Gtk.Label()

        page = SettingsPage()
        self.builder.get_object("box1").pack_start(page, True, True, 0)

        language_settings = page.add_section()

        label = Gtk.Label.new()
        label.set_markup("<b>%s</b>\n<small>%s</small>" % (_("Language"), _("Language, interface, date and time...")))
        row = SettingsRow(label, self.locale_button)
        language_settings.add_row(row)

        label = Gtk.Label.new()
        label.set_markup("<b>%s</b>\n<small>%s</small>" % (_("Region"), _("Numbers, currency, addresses, measurement...")))
        row = SettingsRow(label, self.region_button)
        language_settings.add_row(row)

        self.system_row = SettingsRow(self.system_label, self.locale_system_wide_button)
        self.system_row.set_no_show_all(True)
        language_settings.add_row(self.system_row)

        self.install_row = SettingsRow(self.install_label, self.locale_install_button)
        self.install_row.set_no_show_all(True)
        if IS_DEBIAN:
            language_settings.add_row(self.install_row)

        self.pam_environment_path = os.path.join(GLib.get_home_dir(), ".pam_environment")
        self.dmrc_path = os.path.join(GLib.get_home_dir(), ".dmrc")
        self.dmrc = configparser.ConfigParser()
        self.dmrc.optionxform = str  # force case sensitivity on ConfigParser
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

        print("User language in .dmrc: %s" % dmrc_language)
        print("User language in $LANG: %s" % env_language)
        print("Current language: %s" % self.current_language)

        if 'LC_NUMERIC' in os.environ:
            self.current_region = os.environ['LC_NUMERIC']
        else:
            self.current_region = self.current_language

        if os.path.exists(self.pam_environment_path):
            with codecs.open(self.pam_environment_path, 'r', encoding='UTF-8') as pam_file:
                for line in pam_file:
                    line = line.strip()
                    if line.startswith("LC_NUMERIC="):
                        self.current_region = line.split("=")[1].replace("\"", "").replace("'", "").strip()

        print("Current region: %s" % self.current_region)

        # Replace utf8 with UTF-8 (lightDM GTK greeter messes that up)
        self.current_language = self.current_language.replace(".utf8", ".UTF-8")
        self.current_region = self.current_region.replace(".utf8", ".UTF-8")

        self.build_lang_list()
        self.set_system_locale()
        self.set_num_installed()

        self.accountService = AccountsService.UserManager.get_default().get_user(current_user)
        self.accountService.connect('notify::is-loaded', self.accountservice_ready)
        self.accountService.connect('changed::', self.accountservice_changed)

        groups = grp.getgrall()
        for group in groups:
            (name, pw, gid, mem) = group
            if name in ("adm", "sudo", "wheel", "root"):
                for user in mem:
                    if current_user == user:
                        self.system_row.set_no_show_all(False)
                        self.install_row.set_no_show_all(False)
                        language_settings.show_all()
                        break

        self.window.show_all()

    def button_system_language_clicked(self, button):
        print("Setting system locale: language '%s', region '%s'" % (self.current_language, self.current_region))
        subprocess.call(['pkexec', 'set-default-locale', self.locale_path, self.current_language, self.current_region])
        self.set_system_locale()
        pass

    def button_install_remove_clicked(self, button):
        os.system("pkexec add-remove-locales")
        self.build_lang_list()
        self.set_system_locale()
        self.set_num_installed()

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

    def set_system_locale(self):
        language_str = _("No locale defined")
        region_str = _("No locale defined")

        # Get system locale
        if os.path.exists(self.locale_path):
            vars = dict()
            with open(self.locale_path) as f:
                for line in f:
                    eq_index = line.find('=')
                    var_name = line[:eq_index].strip()
                    value = line[eq_index + 1:].strip()
                    vars[var_name] = value
            if "LANG" in vars:
                locale = vars['LANG'].replace('"', '').replace("'", "")
                locale = locale.split(".")[0].strip()
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
                        language_label = u"%s, %s" % (language, country)
                else:
                    if locale in self.languages:
                        language_label = self.languages[locale]
                    else:
                        language_label = locale

                language_str = language_label

            if "LC_NUMERIC" in vars:
                locale = vars['LC_NUMERIC'].replace('"', '').replace("'", "")
                locale = locale.split(".")[0].strip()
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
                        language_label = u"%s, %s" % (language, country)
                else:
                    if locale in self.languages:
                        language_label = self.languages[locale]
                    else:
                        language_label = locale

                region_str = language_label

        language_prefix = ("Language:")
        region_prefix = ("Region:")
        self.system_label.set_markup("<b>%s</b>\n<small>%s <i>%s</i>\n%s <i>%s</i></small>" % (_("System locale"), language_prefix, language_str, region_prefix, region_str))

    def set_num_installed(self):
        num_installed = int(subprocess.check_output("localedef --list-archive | wc -l", shell=True))
        self.install_label.set_markup("<b>%s</b>\n<small>%s</small>" % (_("Language support"), gettext.ngettext("%d language installed", "%d languages installed", num_installed) % num_installed))

    def accountservice_ready(self, user, param):
        self.window.show()

    def accountservice_changed(self, user):
        print("AccountsService language is: '%s'" % user.get_language())

    def build_lang_list(self):

        self.locale_button.clear_menu()
        self.region_button.clear_menu()
        self.locale_button.set_button_label(self.current_language)
        self.region_button.set_button_label(self.current_region)

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

        cur_index = -1  # find the locale :P
        locales = subprocess.check_output("localedef --list-archive", shell=True)
        locales = locales.decode('utf-8')

        all_locales_are_utf8 = True
        for line in locales.split("\n"):
            line = line.replace("utf8", "UTF-8")
            charmap = None
            if len(line.split(".")) > 1:
                charmap = line.split(".")[1].strip()
                if charmap != "UTF-8":
                    all_locales_are_utf8 = False
                    break
            else:
                all_locales_are_utf8 = False
                break

        built_locales = {}
        for line in locales.rstrip().split("\n"):
            line = line.replace("utf8", "UTF-8")
            cur_index += 1
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
                        language_label = u"%s (@%s), %s" % (language, split[1].split('@')[1].strip(), country)
                    else:
                        language_label = u"%s, %s" % (language, country)

                    flag_path = FLAG_PATH % country_code
            else:
                if locale_code in self.languages:
                    language_label = self.languages[locale_code]
                else:
                    language_label = locale_code
                flag_path = FLAG_PATH % locale_code

            flag_path = self.set_minority_language_flag_path(locale_code, flag_path)

            if charmap is not None and not all_locales_are_utf8:
                language_label = u"%s  <small><span foreground='#3c3c3c'>%s</span></small>" % (language_label, charmap)

            if os.path.exists(flag_path):
                flag = flag_path
            else:
                flag = FLAG_PATH % '_generic'

            built_locales[language_label] = (line, flag)

        for language_label, (line, flag) in sorted(built_locales.items()):
            locale = Locale(line, language_label)
            self.locale_button.add_picture(flag, self.set_user_locale, title=language_label, id=locale)
            self.region_button.add_picture(flag, self.set_user_region, title=language_label, id=locale)

            if (line == self.current_language):
                self.locale_button.set_picture_from_file(flag)
                self.locale_button.set_button_label(language_label)

            if (line == self.current_region):
                self.region_button.set_picture_from_file(flag)
                self.region_button.set_button_label(language_label)

        self.locale_button.show_all()
        self.region_button.show_all()

    def set_user_locale(self, path, locale):
        self.locale_button.set_button_label(locale.name)
        print(u"Setting language to %s" % locale.id)
        # Set it in Accounts Service
        try:
            self.accountService.set_language(locale.id)
        except:
            pass

        # Set it in .dmrc
        self.dmrc.set('Desktop', 'Language', locale.id)
        with codecs.open(self.dmrc_path, 'w', encoding='utf-8') as configfile:
            self.dmrc.write(configfile)
        os.system("sed -i 's/ = /=/g' %s" % self.dmrc_path)  # Remove space characters around "="" sign, created by ConfigParser

        self.current_language = locale.id

        # Set it in .pam_environment
        self.set_pam_environment()

        self.locale_system_wide_button.set_sensitive(True)

        return True

    def set_user_region(self, path, locale):
        self.region_button.set_button_label(locale.name)
        print("Setting region to %s" % locale.id)

        # We don't call self.accountService.set_formats_locale(locale.id) here...
        # First, we don't really use AccountsService, we're only doing this to be nice to LightDM and all..
        # Second, it's Ubuntu specific...
        # Third it overwrites LC_TIME in .pam_environment

        self.current_region = locale.id

        # Set it in .pam_environment
        self.set_pam_environment()

        self.locale_system_wide_button.set_sensitive(True)

        return True

    def set_pam_environment(self):
        shortlocale = self.current_language
        if "." in self.current_language:
            shortlocale = self.current_language.split(".")[0]

        if os.path.exists(self.pam_environment_path):

            # Replace values for present fields
            for lc_variable in ['LC_NUMERIC', 'LC_MONETARY', 'LC_PAPER', 'LC_NAME', 'LC_ADDRESS', 'LC_TELEPHONE', 'LC_MEASUREMENT', 'LC_IDENTIFICATION']:
                os.system("sed -i 's/^%s=.*/%s=%s/g' %s" % (lc_variable, lc_variable, self.current_region, self.pam_environment_path))
            for lc_variable in ['LC_TIME', 'LANG']:
                os.system("sed -i 's/^%s=.*/%s=%s/g' %s" % (lc_variable, lc_variable, self.current_language, self.pam_environment_path))
            for lc_variable in ['LANGUAGE']:
                os.system("sed -i 's/^%s=.*/%s=%s/g' %s" % (lc_variable, lc_variable, shortlocale, self.pam_environment_path))

            # Check missing fields
            with codecs.open(self.pam_environment_path, 'r', encoding='utf-8') as file:
                content = file.read()

            for lc_variable in ['LC_NUMERIC', 'LC_MONETARY', 'LC_PAPER', 'LC_NAME', 'LC_ADDRESS', 'LC_TELEPHONE', 'LC_MEASUREMENT', 'LC_IDENTIFICATION']:
                if not (("%s=" % lc_variable) in content or ("%s =" % lc_variable) in content):
                    os.system("echo '%s=%s' >> %s" % (lc_variable, self.current_region, self.pam_environment_path))
            if not ("LC_TIME=" in content or "LC_TIME =" in content):
                os.system("echo 'LC_TIME=%s' >> %s" % (self.current_language, self.pam_environment_path))

            if ("XDG_SEAT_PATH" in os.environ):
                # LightDM
                if not ("PAPERSIZE=" in content or "PAPERSIZE =" in content):
                    os.system("echo 'PAPERSIZE=a4' >> %s" % self.pam_environment_path)
                if not ("LANGUAGE=" in content or "LANGUAGE =" in content):
                    os.system("echo 'LANGUAGE=%s' >> %s" % (shortlocale, self.pam_environment_path))
                if not ("LANG=" in content or "LANG =" in content):
                    os.system("echo 'LANG=%s' >> %s" % (self.current_language, self.pam_environment_path))
            else:
                # MDM
                for lc_variable in ['LANGUAGE', 'LANG']:
                    os.system("sed -i '/^%s=.*/d' %s" % (lc_variable, self.pam_environment_path))

        else:
            if ("XDG_SEAT_PATH" in os.environ):
                # LightDM
                os.system("sed -e 's/$locale/%s/g' -e 's/$shortlocale/%s/g' -e 's/$region/%s/g' /usr/share/linuxmint/mintlocale/templates/lightdm_pam_environment.template > %s" % (self.current_language, shortlocale, self.current_region, self.pam_environment_path))
            else:
                # MDM
                os.system("sed -e 's/$locale/%s/g' -e 's/$region/%s/g' /usr/share/linuxmint/mintlocale/templates/mdm_pam_environment.template > %s" % (self.current_language, self.current_region, self.pam_environment_path))


if __name__ == "__main__":

    MintLocale()
    Gtk.main()

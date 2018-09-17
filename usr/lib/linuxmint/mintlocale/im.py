#!/usr/bin/python3
import apt
import codecs
import gettext
import locale
import mintcommon
import os

try:
    import _thread as thread
except ImportError as err:
    import thread

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('AccountsService', '1.0')
from gi.repository import GdkX11
from gi.repository import Gtk, GObject, Gio, AccountsService, GLib, Gdk, GdkPixbuf, XApp

from ImConfig.ImConfig import ImConfig

# i18n
APP = 'mintlocale'
LOCALE_DIR = "/usr/share/linuxmint/locale"
locale.bindtextdomain(APP, LOCALE_DIR)
gettext.bindtextdomain(APP, LOCALE_DIR)
gettext.textdomain(APP)
_ = gettext.gettext

(IM_CHOICE, IM_NAME) = list(range(2))

GObject.threads_init()

class IMLanguage():

    def __init__(self, codename, methods, button, app):
        self.app = app
        self.packages = []
        self.missing_packages = []
        self.apt = mintcommon.APT(self.app.window)
        self.button = button
        self.button.connect('clicked', self.install)
        self.button.set_sensitive(False)

        # load package list
        info_paths = []
        info_paths.append("/usr/share/linuxmint/mintlocale/iminfo/locale/%s.info" % codename)
        for input_method in methods.split(":"):
            info_paths.append("/usr/share/linuxmint/mintlocale/iminfo/%s.info" % input_method)
        for info_path in info_paths:
            with codecs.open(info_path, encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("#") or line == "":
                        # skip empty lines and comments
                        continue
                    if line not in self.packages:
                        self.packages.append(line)

    def install(self, widget):
        if len(self.missing_packages) > 0:
            self.app.lock_ui()
            if self.app.cache_updated:
                self.apt.set_finished_callback(self.on_install_finished)
                self.apt.set_cancelled_callback(self.on_install_finished)
                self.apt.install_packages(self.missing_packages)
            else:
                self.apt.set_finished_callback(self.on_update_finished)
                self.apt.update_cache()

    def on_update_finished(self, transaction=None, exit_state=None):
        self.app.cache_updated = True
        self.apt.set_finished_callback(self.on_install_finished)
        self.apt.set_cancelled_callback(self.on_install_finished)
        self.apt.install_packages(self.missing_packages)

    def on_install_finished(self, transaction=None, exit_state=None):
        self.app.check_input_methods()

    def update_status(self, cache):
        self.missing_packages = []
        for package in self.packages:
            if package in cache and not cache[package].is_installed:
                self.missing_packages.append(package)
        if len(self.missing_packages) > 0:
            self.button.show()
            self.button.set_sensitive(True)
            self.button.set_tooltip_text("\n".join(self.missing_packages))
        else:
            self.button.set_label(_("Already installed"))
            self.button.set_tooltip_text("")

class IM:

    ''' Create the UI '''

    def __init__(self):

        # Determine path to system locale-config
        self.locale_path=''

        if os.path.exists('/etc/default/locale'):
            self.locale_path='/etc/default/locale'
        else:
            self.locale_path='/etc/locale.conf'

        # Prepare the APT cache
        self.cache = apt.Cache()
        self.cache_updated = False

        # load our glade ui file in
        self.builder = Gtk.Builder()
        self.builder.set_translation_domain("mintlocale")
        self.builder.add_from_file('/usr/share/linuxmint/mintlocale/im.ui')

        self.window = self.builder.get_object("main_window")
        self.window.set_title(_("Input Method"))
        XApp.set_window_icon_name(self.window, "mintlocale-im")
        self.window.connect("destroy", Gtk.main_quit)

        self.im_combo = self.builder.get_object("im_combo")
        model = Gtk.ListStore(GObject.TYPE_STRING, GObject.TYPE_STRING)
        cell = Gtk.CellRendererText()
        self.im_combo.pack_start(cell, True)
        self.im_combo.add_attribute(cell, 'text', IM_NAME)
        self.im_combo.set_model(model)

        self.ImConfig = ImConfig()

        self.im_languages = []
        self.im_languages.append(IMLanguage("zh-hans", "fcitx:ibus", self.builder.get_object("button_szh"), self))
        self.im_languages.append(IMLanguage("zh-hant", "fcitx:ibus", self.builder.get_object("button_tzh"), self))
        self.im_languages.append(IMLanguage("ja", "fcitx:ibus", self.builder.get_object("button_ja"), self))
        self.im_languages.append(IMLanguage("th", "fcitx:ibus", self.builder.get_object("button_th"), self))
        self.im_languages.append(IMLanguage("vi", "fcitx:ibus", self.builder.get_object("button_vi"), self))
        self.im_languages.append(IMLanguage("ko", "fcitx:ibus", self.builder.get_object("button_ko"), self))
        self.im_languages.append(IMLanguage("te", "ibus", self.builder.get_object("button_te"), self))

        self.im_loaded = False  # don't react to im changes until we're fully loaded (we're loading that combo asynchronously)
        self.im_combo.connect("changed", self.on_combobox_input_method_changed)

        self.lock_ui()
        self.check_input_methods()

        self.window.show_all()

    def lock_ui(self):
        self.window.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.WATCH))
        for im in self.im_languages:
            im.button.set_sensitive(False)
        self.im_combo.set_sensitive(False)

    def check_input_methods(self):
        if not self.ImConfig.available():
            self.lock_ui()
            self.toolbar.hide()
            return
        else:
            self.im_combo.set_sensitive(True)

        if not self.im_combo.get_model():
            print("no model")
            return

        thread.start_new_thread(self.check_input_methods_async, ())

    def check_input_methods_async(self):
        self.im_loaded = False

        # slow operations
        currentIM = self.ImConfig.getCurrentInputMethod()
        availableIM = self.ImConfig.getAvailableInputMethods()
        allIM = self.ImConfig.getAllInputMethods()
        GObject.idle_add(self.check_input_methods_update_ui, currentIM, availableIM, allIM)

    def check_input_methods_update_ui(self, currentIM, availableIM, allIM):

        self.cache.open(None)

        for im_language in self.im_languages:
            im_language.update_status(self.cache)

        model = self.im_combo.get_model()
        model.clear()

        # find out about the other options
        names = dict(xim=_('XIM'), ibus='IBus', scim='SCIM', fcitx='Fcitx', uim='UIM', gcin='gcin', hangul='Hangul', thai='Thai')
        iter = model.append()
        model.set_value(iter, IM_CHOICE, "none")
        model.set_value(iter, IM_NAME, _("None"))
        self.im_combo.set_active_iter(iter)
        for (i, IM) in enumerate(availableIM):
            name = names[IM] if IM in names else IM
            iter = model.append()
            model.set_value(iter, IM_CHOICE, IM)
            model.set_value(iter, IM_NAME, name)
            if IM == currentIM:
                self.im_combo.set_active_iter(iter)

        self.window.get_window().set_cursor(None)
        self.im_loaded = True

    def on_combobox_input_method_changed(self, widget):
        if not self.im_loaded:
            # IM info not fully loaded yet, so ignore the signal
            return

        model = self.im_combo.get_model()
        if self.im_combo.get_active() < 0:
            return
        (IM_choice, IM_name) = model[self.im_combo.get_active()]
        self.ImConfig.setInputMethod(IM_choice)


if __name__ == "__main__":

    IM()
    Gtk.main()

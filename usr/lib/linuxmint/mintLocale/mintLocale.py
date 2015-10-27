#!/usr/bin/env python

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('AccountsService', '1.0')
from gi.repository import Gtk, GdkPixbuf, Gdk, GObject, Gio, AccountsService, GLib

from ImConfig.ImConfig import ImConfig

try:
    import os
    import commands
    import sys
    import string
    import gettext
    import ConfigParser
    import grp
    import locale
    import apt
    import tempfile
    import thread
    from subprocess import Popen
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

(IM_CHOICE, IM_NAME) = range(2)

GObject.threads_init()

def list_header_func(row, before, user_data):
    if before and not row.get_header():
        row.set_header(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

class IMInfo():
    def __init__(self):
        self.required = []
        self.optional = []

class Locale():
    def __init__ (self, id, name):
        self.id = id
        self.name = name

class PictureChooserButton (Gtk.Button):

    def __init__ (self, num_cols=4, button_picture_size=None, menu_pictures_size=None, has_button_label=False):
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

    def set_picture_from_file (self, path):
        file = Gio.File.new_for_path(path)
        file_icon = Gio.FileIcon(file=file)
        self.button_image.set_from_gicon(file_icon, Gtk.IconSize.DIALOG)
        if self.menu_pictures_size is not None:
            self.button_image.set_pixel_size(self.menu_pictures_size)

    def set_button_label(self, label):
        self.button_label.set_markup(label)

    def popup_menu_below_button (self, menu, widget):
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

        push_in = True # push_in is True so all menu is always inside screen
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
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(path)
            else:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, -1, self.button_picture_size, True)
            image = Gtk.Image.new_from_pixbuf (pixbuf)
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
            self.menu.attach(menuitem, self.col, self.col+1, self.row, self.row+1)
            self.col = (self.col+1) % self.num_cols
            if (self.col == 0):
                self.row = self.row + 1

    def add_separator(self):
        self.row = self.row + 1
        self.menu.attach(Gtk.SeparatorMenuItem(), 0, self.num_cols, self.row, self.row+1)

    def add_menuitem(self, menuitem):
        self.row = self.row + 1
        self.menu.attach(menuitem, 0, self.num_cols, self.row, self.row+1)

class SettingsPage(Gtk.Box):
    def __init__(self):
        Gtk.Box.__init__(self)
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.set_spacing(15)
        self.set_margin_left(80)
        self.set_margin_right(80)
        self.set_margin_top(15)
        self.set_margin_bottom(15)

    def add_section(self, title):
        section = SettingsBox(title)
        self.pack_start(section, False, False, 0)

        return section

class SettingsBox(Gtk.Frame):
    def __init__(self, title):
        Gtk.Frame.__init__(self)
        self.set_shadow_type(Gtk.ShadowType.IN)
        frame_style = self.get_style_context()
        frame_style.add_class("view")
        self.size_group = Gtk.SizeGroup()
        self.size_group.set_mode(Gtk.SizeGroupMode.VERTICAL)

        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(self.box)

        toolbar = Gtk.Toolbar.new()
        toolbar_context = toolbar.get_style_context()
        Gtk.StyleContext.add_class(Gtk.Widget.get_style_context(toolbar), "cs-header")

        label = Gtk.Label.new()
        label.set_markup("<b>%s</b>" % title)
        title_holder = Gtk.ToolItem()
        title_holder.add(label)
        toolbar.add(title_holder)
        self.box.add(toolbar)

        toolbar_separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        self.box.add(toolbar_separator)
        separator_context = toolbar_separator.get_style_context()
        frame_color = frame_style.get_border_color(Gtk.StateFlags.NORMAL).to_string()
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(".separator { -GtkWidget-wide-separators: 0; \
                                                   color: %s;                    \
                                                }" % frame_color)
        separator_context.add_provider(css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.list_box.set_header_func(list_header_func, None)
        self.box.add(self.list_box)

    def add_row(self, row):
        self.list_box.add(row)

class SettingsRow(Gtk.ListBoxRow):
    def __init__(self, widget):
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

        grid.attach(self.description_box, 0, 0, 1, 1)
        grid.attach_next_to(widget, self.description_box, Gtk.PositionType.RIGHT, 1, 1)

    def add_label(self, label):
        label.props.xalign = 0.0
        self.description_box.add(label)

class MintLocale:

    ''' Create the UI '''
    def __init__(self, show_input_methods):

        # load our glade ui file in
        self.builder = Gtk.Builder()
        self.builder.set_translation_domain("mintlocale")
        self.builder.add_from_file('/usr/lib/linuxmint/mintLocale/mintLocale.ui')

        self.window = self.builder.get_object( "main_window" )

        self.builder.get_object("main_window").connect("destroy", Gtk.main_quit)

        # set up larger components.
        self.builder.get_object("main_window").set_title(_("Language Settings"))

        toolbar = Gtk.Toolbar()
        toolbar.get_style_context().add_class("primary-toolbar")
        self.builder.get_object("box1").pack_start(toolbar, False, False, 0)

        stack = Gtk.Stack()
        stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        stack.set_transition_duration(150)
        self.builder.get_object("box1").pack_start(stack, True, True, 0)

        stack_switcher = Gtk.StackSwitcher()
        stack_switcher.set_stack(stack)

        tool_item = Gtk.ToolItem()
        tool_item.set_expand(True)
        tool_item.get_style_context().add_class("raised")
        toolbar.insert(tool_item, 0)
        switch_holder = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        switch_holder.set_border_width(1)
        tool_item.add(switch_holder)
        switch_holder.pack_start(stack_switcher, True, True, 0)
        stack_switcher.set_halign(Gtk.Align.CENTER)
        toolbar.show_all()

        size_group = Gtk.SizeGroup.new(Gtk.SizeGroupMode.HORIZONTAL)

        self.locale_button = PictureChooserButton(num_cols=2, button_picture_size=16, has_button_label=True)
        size_group.add_widget(self.locale_button)
        self.region_button = PictureChooserButton(num_cols=2, button_picture_size=16, has_button_label=True)
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
        stack.add_titled(page, "language", _("Language"))

        language_settings = page.add_section(_("Language"))

        row = SettingsRow(self.locale_button)
        label = Gtk.Label.new()
        label.set_markup("<b>%s</b>\n<small>%s</small>" % (_("Language"), _("Language, interface, date and time...")))
        row.add_label(label)
        language_settings.add_row(row)

        row = SettingsRow(self.region_button)
        label = Gtk.Label.new()
        label.set_markup("<b>%s</b>\n<small>%s</small>" % (_("Region"), _("Numbers, currency, addresses, measurement...")))
        row.add_label(label)
        language_settings.add_row(row)

        self.system_row = SettingsRow(self.locale_system_wide_button)
        self.system_row.add_label(self.system_label)
        self.system_row.set_no_show_all(True)
        language_settings.add_row(self.system_row)

        self.install_row = SettingsRow(self.locale_install_button)
        self.install_row.add_label(self.install_label)
        self.install_row.set_no_show_all(True)
        language_settings.add_row(self.install_row)

        page = SettingsPage()
        stack.add_titled(page, "input settings", _("Input method"))

        size_group = Gtk.SizeGroup.new(Gtk.SizeGroupMode.HORIZONTAL)

        self.im_combo = Gtk.ComboBox()
        model = Gtk.ListStore(GObject.TYPE_STRING, GObject.TYPE_STRING)
        cell = Gtk.CellRendererText()
        self.im_combo.pack_start(cell, True)
        self.im_combo.add_attribute(cell, 'text', IM_NAME)
        self.im_combo.set_model(model)
        size_group.add_widget(self.im_combo)

        self.ImConfig = ImConfig()

        label = Gtk.Label()
        label.set_markup("<small><i>%s</i></small>" % (_("Input methods are used to write symbols and characters which are not present on the keyboard. They are useful to write in Chinese, Japanese, Korean, Thai, Vietnamese...")))
        label.set_line_wrap(True)
        page.add(label)

        self.input_settings = page.add_section(_("Input method"))

        row = SettingsRow(self.im_combo)
        label = Gtk.Label(_("Input method"))
        row.add_label(label)
        self.input_settings.add_row(row)

        self.ibus_label = Gtk.Label()
        self.ibus_label.set_line_wrap(True)
        self.ibus_button = Gtk.Button()
        size_group.add_widget(self.ibus_button)
        self.ibus_button.connect('clicked', self.install_im, 'ibus')
        self.ibus_row = SettingsRow(self.ibus_button)
        self.ibus_row.add_label(self.ibus_label)
        self.ibus_row.set_no_show_all(True)
        self.input_settings.add_row(self.ibus_row)

        self.fcitx_label = Gtk.Label()
        self.fcitx_label.set_line_wrap(True)
        self.fcitx_button = Gtk.Button()
        size_group.add_widget(self.fcitx_button)
        self.fcitx_button.connect('clicked', self.install_im, 'fcitx')
        self.fcitx_row = SettingsRow(self.fcitx_button)
        self.fcitx_row.add_label(self.fcitx_label)
        self.fcitx_row.set_no_show_all(True)
        self.input_settings.add_row(self.fcitx_row)

        self.scim_label = Gtk.Label()
        self.scim_label.set_line_wrap(True)
        self.scim_button = Gtk.Button()
        size_group.add_widget(self.scim_button)
        self.scim_button.connect('clicked', self.install_im, 'scim')
        self.scim_row = SettingsRow(self.scim_button)
        self.scim_row.add_label(self.scim_label)
        self.scim_row.set_no_show_all(True)
        self.input_settings.add_row(self.scim_row)

        self.uim_label = Gtk.Label()
        self.uim_label.set_line_wrap(True)
        self.uim_button = Gtk.Button()
        size_group.add_widget(self.uim_button)
        self.uim_button.connect('clicked', self.install_im, 'uim')
        self.uim_row = SettingsRow(self.uim_button)
        self.uim_row.add_label(self.uim_label)
        self.uim_row.set_no_show_all(True)
        self.input_settings.add_row(self.uim_row)

        self.gcin_label = Gtk.Label()
        self.gcin_label.set_line_wrap(True)
        self.gcin_button = Gtk.Button()
        size_group.add_widget(self.gcin_button)
        self.gcin_button.connect('clicked', self.install_im, 'gcin')
        self.gcin_row = SettingsRow(self.gcin_button)
        self.gcin_row.add_label(self.gcin_label)
        self.gcin_row.set_no_show_all(True)
        self.input_settings.add_row(self.gcin_row)

        self.im_loaded = False # don't react to im changes until we're fully loaded (we're loading that combo asynchronously)
        self.im_combo.connect("changed", self.on_combobox_input_method_changed)

        stack.show_all()

        self.pam_environment_path = os.path.join(GLib.get_home_dir(), ".pam_environment")
        self.dmrc_path = os.path.join(GLib.get_home_dir(), ".dmrc")
        self.dmrc = ConfigParser.ConfigParser()
        self.dmrc.optionxform=str # force case sensitivity on ConfigParser
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

        if 'LC_NUMERIC' in os.environ:
            self.current_region = os.environ['LC_NUMERIC']
        else:
            self.current_region = self.current_language

        if os.path.exists(self.pam_environment_path):
            with open(self.pam_environment_path, 'r') as pam_file:
                for line in pam_file:
                    line = line.strip()
                    if line.startswith("LC_NUMERIC="):
                        self.current_region = line.split("=")[1].replace("\"", "").replace("'", "").strip()

        print "Current region: %s" % self.current_region

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
            if name in ("adm", "sudo"):
                for user in mem:
                    if current_user == user:
                        self.system_row.set_no_show_all(False)
                        self.install_row.set_no_show_all(False)
                        language_settings.show_all()
                        self.ibus_row.set_no_show_all(False)
                        self.fcitx_row.set_no_show_all(False)
                        self.scim_row.set_no_show_all(False)
                        self.uim_row.set_no_show_all(False)
                        self.gcin_row.set_no_show_all(False)
                        self.input_settings.hide()
                        break

        self.read_im_info()
        self.check_input_methods()

        if (show_input_methods):
            page.show()
            stack.set_visible_child(page)

    def button_system_language_clicked (self, button):
        print "Setting system locale: language '%s', region '%s'" % (self.current_language, self.current_region)
        os.system("gksu set-default-locale '%s' '%s'" % (self.current_language, self.current_region))
        self.set_system_locale()
        pass

    def button_install_remove_clicked (self, button):
        os.system("gksu add-remove-locales")
        self.build_lang_list()
        self.set_system_locale()
        self.set_num_installed()

    def read_im_info(self):
        self.im_info = {}

        # use specific im_info file if exists
        im_info_path = "/usr/lib/linuxmint/mintLocale/iminfo/{0}.info".format(self.current_language.split(".")[0].split("_")[0])
        if not os.path.exists(im_info_path):
            im_info_path = "/usr/lib/linuxmint/mintLocale/iminfo/other.info"

        with open(im_info_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("#") or line == "":
                    # skip empty lines and comments
                    continue
                (im, urgency, package) = line.split("\t")
                if not self.im_info.has_key(im):
                    self.im_info[im] = IMInfo()
                info = self.im_info[im]
                if urgency == 'required':
                    info.required.append(package)
                elif urgency == 'optional':
                    info.optional.append(package)

    def install_im(self, button, im):
        to_install = self.to_install[im]
        if to_install is not None and len(to_install) > 0:
            cmd = ["pkexec", "/usr/sbin/synaptic", "--hide-main-window", "--non-interactive"]
            cmd.append("-o")
            cmd.append("Synaptic::closeZvt=true")
            cmd.append("--progress-str")
            cmd.append("\"" + _("Please wait, this can take some time") + "\"")
            cmd.append("--finish-str")
            cmd.append("\"" + _("Installation is complete") + "\"")
            f = tempfile.NamedTemporaryFile()
            for pkg in to_install:
                f.write("%s\tinstall\n" % pkg)
            cmd.append("--set-selections-file")
            cmd.append("%s" % f.name)
            f.flush()
            comnd = Popen(' '.join(cmd), shell=True)
            returnCode = comnd.wait()
            f.close()
        self.check_input_methods()

    def check_input_methods(self):
        if not self.ImConfig.available():
            self.im_combo.set_sensitive(False)
            return

        if not self.im_combo.get_model():
            print "no model"
            return

        thread.start_new_thread(self.check_input_methods_async, ())

    def check_input_methods_async(self):
        self.im_loaded = False

        # slow operations
        currentIM = self.ImConfig.getCurrentInputMethod()
        availableIM = self.ImConfig.getAvailableInputMethods()
        allIM = self.ImConfig.getAllInputMethods()
        cache = apt.Cache()
        GObject.idle_add(self.check_input_methods_update_ui, currentIM, availableIM, allIM, cache)

    def check_input_methods_update_ui(self, currentIM, availableIM, allIM, cache):
        model = self.im_combo.get_model()
        model.clear()

        # find out about the other options
        names = dict(xim=_('None'), ibus='IBus', scim='SCIM', fcitx='Fcitx', uim='UIM', gcin='gcin', hangul='Hangul', thai='Thai')
        for (i, IM) in enumerate(availableIM):
            name = names[IM] if IM in names else IM
            iter = model.append()
            model.set_value(iter, IM_CHOICE, IM)
            model.set_value(iter, IM_NAME, name)
            if IM == currentIM:
                self.im_combo.set_active(i)

        links = dict(ibus='https://code.google.com/p/ibus/', fcitx='https://fcitx-im.org', scim='http://sourceforge.net/projects/scim/', uim='https://code.google.com/p/uim/', gcin='http://hyperrate.com/dir.php?eid=67')
        gtklabels = dict(ibus=self.ibus_label, fcitx=self.fcitx_label, scim=self.scim_label, uim=self.uim_label, gcin=self.gcin_label)
        gtkbuttons = dict(ibus=self.ibus_button, fcitx=self.fcitx_button, scim=self.scim_button, uim=self.uim_button, gcin=self.gcin_button)

        self.to_install = {}

        for (i, IM) in enumerate(allIM):
            name = names[IM] if IM in names else IM
            if IM in gtklabels:
                self.to_install[IM] = []
                gtklabel = gtklabels[IM]
                gtkbutton = gtkbuttons[IM]
                gtkbutton.set_label('')
                gtkbutton.set_tooltip_text('')
                gtkbutton.hide()
                if IM in cache:
                    pkg = cache[IM]
                    missing = []
                    optional = []
                    for req in self.im_info[IM].required:
                        if req in cache and not cache[req].is_installed:
                            missing.append(req)
                    for req in self.im_info[IM].optional:
                        if req in cache and not cache[req].is_installed:
                            optional.append(req)
                    if pkg.is_installed:
                        status = "<span foreground='#4ba048'>%s</span>" % _("Installed")
                        if len(missing) > 0:
                            status = "<span foreground='#a04848'>%s</span>" % (_("%d missing components!") % len(missing))
                            gtkbutton.set_label(_("Install the missing components"))
                            gtkbutton.set_tooltip_text('\n'.join(missing))
                            gtkbutton.show()
                            self.to_install[IM] = missing
                        elif len(optional) > 0:
                            status = "<span foreground='#4ba048'>%s</span>" % (_("%d optional components available") % len(optional))
                            gtkbutton.set_label(_("Install the optional components"))
                            gtkbutton.set_tooltip_text('\n'.join(optional))
                            gtkbutton.show()
                            self.to_install[IM] = optional
                    else:
                        status = "%s" % _("Not installed")
                        gtkbutton.set_label(_("Add support for %s") % name)
                        gtkbutton.set_tooltip_text('\n'.join(missing))
                        gtkbutton.show()
                        self.to_install[IM] = missing

                    gtklabel.set_markup("<a href='%s'>%s</a>\n<small>%s</small>" % (links[IM], name, status))

                else:
                    gtklabel.set_markup("%s\n<small>%s</small>" % (name, _("Not supported")))

        self.input_settings.show_all()
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

    # Checks for minority languages that have a flag and returns the corresponding flag_path or the unchanged flag_path
    def set_minority_language_flag_path(self, locale_code, flag_path):
        # Get the language code from the locale_code. For example, Basque's locale code can be eu or eu_es or eu_fr, Welsh's cy or cy_gb...
        language_code = locale_code.split("_")[0]

        if language_code == 'ca':
            flag_path = '/usr/share/linuxmint/mintLocale/flags/16/_Catalonia.png'
        elif language_code == 'cy':
            flag_path = '/usr/share/linuxmint/mintLocale/flags/16/_Wales.png'
        elif language_code == 'eu':
            flag_path = '/usr/share/linuxmint/mintLocale/flags/16/_Basque Country.png'
        elif language_code == 'gl':
            flag_path = '/usr/share/linuxmint/mintLocale/flags/16/_Galicia.png'

        return flag_path

    def set_system_locale(self):
        language_str = _("No locale defined")
        region_str = _("No locale defined")

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
                        language_label = "%s, %s" % (language, country)
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
                        language_label = "%s, %s" % (language, country)
                else:
                    if locale in self.languages:
                        language_label = self.languages[locale]
                    else:
                        language_label = locale

                region_str = language_label

        language_prefix = ("Language:")
        region_prefix = ("Region:")
        self.system_label.set_markup("<b>%s</b>\n<small>%s <i>%s</i>\n%s <i>%s</i></small>" % (_("System locale"), language_prefix, language_str, region_prefix, region_str))

    def set_num_installed (self):
        num_installed = int(commands.getoutput("localedef --list-archive | wc -l"))
        self.install_label.set_markup("<b>%s</b>\n<small>%s</small>" % (_("Language support"), _("%d languages installed") % num_installed))

    def accountservice_ready(self, user, param):
        self.builder.get_object("main_window").show()

    def accountservice_changed(self, user):
        print "AccountsService language is: '%s'" % user.get_language()

    def build_lang_list(self):

        self.locale_button.clear_menu()
        self.region_button.clear_menu()
        self.locale_button.set_button_label(self.current_language)
        self.region_button.set_button_label(self.current_region)

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
        locales = commands.getoutput("localedef --list-archive")

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

        for line in locales.split("\n"):
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

            flag_path = self.set_minority_language_flag_path(locale_code, flag_path)

            if charmap is not None and not all_locales_are_utf8:
                language_label = "%s  <small><span foreground='#3c3c3c'>%s</span></small>" % (language_label, charmap)

            if os.path.exists(flag_path):
                flag = flag_path
            else:
                flag = '/usr/share/linuxmint/mintLocale/flags/16/generic.png'
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
        print "Setting language to %s" % locale.id
        # Set it in Accounts Service
        try:
            self.accountService.set_language(locale.id)
        except:
            pass

        # Set it in .dmrc
        self.dmrc.set('Desktop','Language', locale.id)
        with open(self.dmrc_path, 'wb') as configfile:
            self.dmrc.write(configfile)
        os.system("sed -i 's/ = /=/g' %s" % self.dmrc_path) # Remove space characters around "="" sign, created by ConfigParser

        # Set it in .pam_environment
        if os.path.exists(self.pam_environment_path):
            for lc_variable in ['LANGUAGE', 'LANG']:
                os.system("sed -i '/^%s=.*/d' %s" % (lc_variable, self.pam_environment_path))
            for lc_variable in ['LC_TIME']:
                os.system("sed -i 's/^%s=.*/%s=%s/g' %s" % (lc_variable, lc_variable, locale.id, self.pam_environment_path))
        else:
            os.system("sed -e 's/$locale/%s/g' -e 's/$region/%s/g' /usr/lib/linuxmint/mintLocale/default_pam_environment.template > %s" % (locale.id, self.current_region, self.pam_environment_path))

        self.current_language = locale.id
        self.locale_system_wide_button.set_sensitive(True)

        return True

    def set_user_region(self, path, locale):
        self.region_button.set_button_label(locale.name)
        print "Setting region to %s" % locale.id

        # We don't call self.accountService.set_formats_locale(locale.id) here...
        # First, we don't really use AccountsService, we're only doing this to be nice to LightDM and all..
        # Second, it's Ubuntu specific...
        # Third it overwrites LC_TIME in .pam_environment

        # Set it in .pam_environment
        if os.path.exists(self.pam_environment_path):
            for lc_variable in ['LC_NUMERIC', 'LC_MONETARY', 'LC_PAPER', 'LC_NAME', 'LC_ADDRESS', 'LC_TELEPHONE', 'LC_MEASUREMENT', 'LC_IDENTIFICATION']:
                os.system("sed -i 's/^%s=.*/%s=%s/g' %s" % (lc_variable, lc_variable, locale.id, self.pam_environment_path))
        else:
            os.system("sed -e 's/$locale/%s/g' -e 's/$region/%s/g' /usr/lib/linuxmint/mintLocale/default_pam_environment.template > %s" % (self.current_language, locale.id, self.pam_environment_path))

        self.current_region = locale.id
        self.locale_system_wide_button.set_sensitive(True)

        return True

if __name__ == "__main__":

    if len(sys.argv) > 1 and sys.argv[1] == "im":
        print ("Starting mintlocale in IM mode")
        show_input_methods = True
    else:
        print ("Starting mintlocale")
        show_input_methods = False

    MintLocale(show_input_methods)
    Gtk.main()

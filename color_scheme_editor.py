import sublime
import sublime_plugin
import sys
from os.path import join, exists, basename, normpath, dirname, isfile
from os import listdir, makedirs, chmod, unlink
from os import stat as osstat
import stat
import subprocess

from .lib.package_search import PackageSearch
from .lib.binary_manager import get_binary_location

APP_NAME = "subclrschm"
PLUGIN_NAME = "ColorSchemeEditor"
TEMP_FOLDER = "ColorSchemeEditorTemp"
TEMP_PATH = "Packages/User/%s" % TEMP_FOLDER
PLUGIN_SETTINGS = 'color_scheme_editor.sublime-settings'
PREFERENCES = 'Preferences.sublime-settings'
SCHEME = "color_scheme"
THEMES = "theme-list.sublime-settings"


MSGS = {
    "missing": '''Cannot find Color Scheme Editor!''',

    "access": '''Color Scheme Editor:
There was a problem calling subclrschm.
''',

    "temp": '''Color Scheme Editor:
Could not copy theme file to temp directory.
''',

    "new": '''Color Scheme Editor:
Could not create new theme.
''',

    "download": '''Color Scheme Editor:
Subclrschm binary has not been downloaded.

Would you like to download the subclrschm binary now?
''',

    "no_updates": '''Color Scheme Editor:
No updates available at this time.
'''
}

if sys.platform.startswith('win'):
    _PLATFORM = "windows"
elif sys.platform == "darwin":
    _PLATFORM = "osx"
else:
    _PLATFORM = "linux"


def get_environ():
    """Get environment and force utf-8."""

    import os
    env = {}
    env.update(os.environ)

    if _PLATFORM != 'windows':
        shell = env['SHELL']
        p = subprocess.Popen(
            [shell, '-l', '-c', 'echo "#@#@#${PATH}#@#@#"'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        result = p.communicate()[0].decode('utf8').split('#@#@#')
        if len(result) > 1:
            bin_paths = result[1].split(':')
            if len(bin_paths):
                env['PATH'] = ':'.join(bin_paths)

    env['PYTHONIOENCODING'] = 'utf8'
    env['LANG'] = 'en_US.UTF-8'
    env['LC_CTYPE'] = 'en_US.UTF-8'

    return env


def load_resource(resource, binary=False):
    """Load the given resource."""

    bfr = None
    if not binary:
        bfr = sublime.load_resource(resource)
    else:
        bfr = sublime.load_binary_resource(resource)
    return bfr


class ColorSchemeEditorCommand(sublime_plugin.ApplicationCommand):
    def init_settings(self, action, select_theme):
        """Initialize the settings."""

        init_okay = True
        # Get current color scheme
        self.p_settings = sublime.load_settings(PLUGIN_SETTINGS)
        self.settings = sublime.load_settings(PREFERENCES)
        self.direct_edit = bool(self.p_settings.get("direct_edit", False))
        self.scheme_file = self.settings.get(SCHEME, None)
        self.actual_scheme_file = None
        self.file_select = False

        if action == "select":
            if select_theme is not None:
                self.scheme_file = select_theme
            else:
                init_okay = False
        return init_okay

    def prepare_theme(self, action):
        """Prepare the theme to be edited."""

        if action != "new" and self.scheme_file is not None and (action == "current" or action == "select"):
            # Get real path
            self.actual_scheme_file = join(dirname(sublime.packages_path()), normpath(self.scheme_file))

            # If scheme cannot be found, it is most likely in an archived package
            if (
                not exists(self.actual_scheme_file) or
                (not self.direct_edit and not self.scheme_file.startswith(TEMP_PATH))
            ):
                # Create temp folder
                zipped_themes = join(sublime.packages_path(), "User", TEMP_FOLDER)
                if not exists(zipped_themes):
                    makedirs(zipped_themes)

                # Read theme file into memory and write out to the temp directory
                text = load_resource(self.scheme_file, binary=True)
                self.actual_scheme_file = join(zipped_themes, basename(self.scheme_file))
                try:
                    with open(self.actual_scheme_file, "wb") as f:
                        f.write(text)
                except:
                    sublime.error_message(MSGS["temp"])
                    return

                # Load unarchived theme
                self.settings.set(SCHEME, "%s/%s" % (TEMP_PATH, basename(self.scheme_file)))
            elif action == "select":
                self.settings.set(SCHEME, self.scheme_file)
        elif action != "new" and action != "select":
            self.file_select = True

    def is_live_edit(self, live_edit):
        """Check if we should use live edit."""

        return (
            (live_edit is None and bool(self.p_settings.get("live_edit", True))) or
            (live_edit is not None and live_edit)
        )

    def is_actual_scheme_file(self):
        """Check if actual scheme file."""

        return self.actual_scheme_file is not None and exists(self.actual_scheme_file)

    def run(self, action=None, select_theme=None, live_edit=None):
        """Run subclrschm."""

        # Init settings.  Bail if returned an issue
        if not self.init_settings(action, select_theme):
            return

        # Prepare the theme to be edited
        # Copy to a temp location if desired before editing
        self.prepare_theme(action)

        # Call the editor with the theme file
        try:
            subprocess.Popen(
                [APP_NAME] +
                (["-d"] if bool(self.p_settings.get("debug", False)) else []) +
                (["-n"] if action == "new" else []) +
                (["-s"] if self.file_select else []) +
                (["-L"] if self.is_live_edit(live_edit) else []) +
                ["-l", join(sublime.packages_path(), "User")] +
                ([self.actual_scheme_file] if self.is_actual_scheme_file() else []),
                env=get_environ()
            )
        except Exception as e:
            print(e)
            sublime.error_message(MSGS["access"])


class GetColorSchemeFilesCommand(sublime_plugin.WindowCommand, PackageSearch):

    """Get color scheme files."""

    def on_select(self, value, settings):
        """Process selected menu item."""

        if value != -1:
            preferences = sublime.load_settings(PREFERENCES)
            preferences.set(SCHEME, settings[value])

    def process_file(self, value, settings):
        """Process the file."""

        if value != -1:
            if self.edit:
                sublime.run_command(
                    "color_scheme_editor",
                    {"action": "select", "select_theme": settings[value]}
                )
            else:
                preferences = sublime.load_settings(PREFERENCES)
                preferences.set(SCHEME, settings[value])
        else:
            if self.current_color_scheme is not None:
                preferences = sublime.load_settings(PREFERENCES)
                preferences.set(SCHEME, self.current_color_scheme)

    def pre_process(self, **kwargs):
        """Pre-process actions."""

        self.edit = kwargs.get("edit", True)
        self.current_color_scheme = sublime.load_settings("Preferences.sublime-settings").get("color_scheme")
        return {"pattern": "*.tmTheme"}

    def run(self, **kwargs):
        """Run the command."""

        self.search(**kwargs)


class ColorSchemeEditorLogCommand(sublime_plugin.WindowCommand):

    """Color scheme editor log command."""

    def run(self):
        """Run the command."""

        log = join(sublime.packages_path(), "User", "subclrschm.log")
        if exists(log):
            self.window.open_file(log)


class ColorSchemeClearTempCommand(sublime_plugin.ApplicationCommand):

    """Color scheme editor clear temp folder command."""

    def run(self):
        """Run the command."""

        current_scheme = sublime.load_settings(PREFERENCES).get(SCHEME)
        using_temp = current_scheme.startswith(TEMP_PATH)
        folder = join(sublime.packages_path(), "User", TEMP_FOLDER)
        for f in listdir(folder):
            pth = join(folder, f)
            try:
                if (
                    isfile(pth) and
                    (
                        not using_temp or (
                            basename(pth) != basename(current_scheme) and
                            basename(pth) != basename(current_scheme) + ".JSON"
                        )
                    )
                ):
                    unlink(pth)
            except:
                print("ColorSchemeEditor: Could not remove %s!" % pth)


def init_plugin():
    """Init the plugin."""

    global THEME_EDITOR
    platform = sublime.platform()
    p_settings = sublime.load_settings(PLUGIN_SETTINGS)
    p_settings.clear_on_change('reload')
    p_settings.add_on_change('reload', init_plugin)


def plugin_loaded():
    """Load the plugin."""

    sublime.set_timeout(init_plugin, 3000)

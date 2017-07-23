"""Scheme Editor."""
import sublime
import sublime_plugin
import sys
import os
import subprocess

from .lib.package_search import PackageSearch

TEMP_FOLDER = "SchemeEditorTemp"
TEMP_PATH = "Packages/User/%s" % TEMP_FOLDER
PLUGIN_SETTINGS = 'scheme_editor.sublime-settings'
PREFERENCES = 'Preferences.sublime-settings'
SCHEME = "color_scheme"


MSGS = {
    "access": '''Scheme Editor:
There was a problem calling subclrschm.
''',

    "temp": '''Scheme Editor:
Could not copy theme file to temp directory.
''',

    "new": '''Scheme Editor:
Could not create new theme.
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


class SchemeEditorCommand(sublime_plugin.ApplicationCommand):
    """Color scheme editor command."""

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
            self.actual_scheme_file = os.path.join(
                os.path.dirname(sublime.packages_path()), os.path.normpath(self.scheme_file)
            )

            # If scheme cannot be found, it is most likely in an archived package
            if (
                not os.path.exists(self.actual_scheme_file) or
                (not self.direct_edit and not self.scheme_file.startswith(TEMP_PATH))
            ):
                # Create temp folder
                zipped_themes = os.path.join(sublime.packages_path(), "User", TEMP_FOLDER)
                if not os.path.exists(zipped_themes):
                    os.makedirs(zipped_themes)

                # Read theme file into memory and write out to the temp directory
                text = load_resource(self.scheme_file, binary=True)
                self.actual_scheme_file = os.path.join(zipped_themes, os.path.basename(self.scheme_file))
                try:
                    with open(self.actual_scheme_file, "wb") as f:
                        f.write(text)
                except:
                    sublime.error_message(MSGS["temp"])
                    return

                # Load unarchived theme
                self.settings.set(SCHEME, "%s/%s" % (TEMP_PATH, os.path.basename(self.scheme_file)))
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

        return self.actual_scheme_file is not None and os.path.exists(self.actual_scheme_file)

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
            cmd = (
                self.p_settings.get('editor', {}).get(sublime.platform(), ['python', '-m', 'subclrschm']) +
                (["--debug"] if bool(self.p_settings.get("debug", False)) else []) +
                (["-n"] if action == "new" else []) +
                (["-s"] if self.file_select else []) +
                (["-L"] if self.is_live_edit(live_edit) else []) +
                ["-l", os.path.join(sublime.packages_path(), "User")] +
                ([self.actual_scheme_file] if self.is_actual_scheme_file() else [])
            )
            print(cmd)
            subprocess.Popen(
                cmd,
                env=get_environ()
            )
        except Exception as e:
            print("SchemeEditor: " + str(e))
            sublime.error_message(MSGS["access"])


class SchemeEditorGetSchemeCommand(sublime_plugin.WindowCommand, PackageSearch):
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
                    "scheme_editor",
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


class SchemeEditorLogCommand(sublime_plugin.WindowCommand):
    """Color scheme editor log command."""

    def run(self):
        """Run the command."""

        log = os.path.join(sublime.packages_path(), "User", "subclrschm.log")
        if os.path.exists(log):
            self.window.open_file(log)


class SchemeEditorClearTempCommand(sublime_plugin.ApplicationCommand):
    """Color scheme editor clear temp folder command."""

    def run(self):
        """Run the command."""

        current_scheme = sublime.load_settings(PREFERENCES).get(SCHEME)
        using_temp = current_scheme.startswith(TEMP_PATH)
        folder = os.path.join(sublime.packages_path(), "User", TEMP_FOLDER)
        for f in os.listdir(folder):
            pth = os.path.join(folder, f)
            try:
                if (
                    os.path.isfile(pth) and
                    (
                        not using_temp or (
                            os.path.basename(pth) != os.path.basename(current_scheme)
                        )
                    )
                ):
                    os.unlink(pth)
            except:
                print("SchemeEditor: Could not remove %s!" % pth)


def delete_old_binary():
    """Delete old binary."""

    import shutil

    binpath = os.path.normpath("${Packages}/User/subclrschm").replace("${Packages}", sublime.packages_path())
    osbinpath = os.path.join(binpath, "subclrschm-bin-%s" % sublime.platform())
    try:
        if os.path.exists(binpath):
            if os.path.isdir(binpath):
                if os.path.exists(osbinpath):
                    shutil.rmtree(osbinpath, onerror=on_rm_error)
            else:
                os.unlink(binpath)
    except Exception as e:
        print("SchemeEditor: " + str(e))


def on_rm_error(func, path, exc_info):
    """Try and handle rare windows delete issue gracefully."""

    import stat

    # excvalue = exc_info[1]
    if func in (os.rmdir, os.unlink):
        os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)  # 0777
        try:
            func(path)
        except:
            if sublime.platform() == "windows":
                # Why are you being so stubborn windows?
                # This situation only randomly occurs
                print("SchemeEditor: Windows is being stubborn...go through rmdir to remove temp folder")
                cmd = ["rmdir", "/S", path]
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                process = subprocess.Popen(
                    cmd,
                    startupinfo=startupinfo,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.PIPE,
                    shell=False
                )
                returncode = process.returncode
                if returncode:
                    print("SchemeEditor: Why won't you play nice, Windows!")
                    print("SchemeEditor:\n" + str(process.communicate()[0]))
                    raise
            else:
                raise
    else:
        raise


def init_plugin():
    """Init the plugin."""

    delete_old_binary()
    p_settings = sublime.load_settings(PLUGIN_SETTINGS)
    p_settings.clear_on_change('reload')
    p_settings.add_on_change('reload', init_plugin)


def plugin_loaded():
    """Load the plugin."""

    sublime.set_timeout(init_plugin, 3000)

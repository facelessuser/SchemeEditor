import sublime
import sublime_plugin
from os.path import join, exists, basename, normpath, dirname, isdir, splitext, isfile, splitdrive, split
from os import listdir, walk, makedirs, chmod, unlink, curdir, pardir
from os import stat as osstat, remove
import stat
from fnmatch import fnmatch
import re
import subprocess
import re
import json
import codecs
from plistlib import writePlistToBytes
from .lib.package_search import PackageSearch, sublime_package_paths
import shutil
import tempfile
import urllib.request as request
import zipfile
from .lib.file_strip.json import sanitize_json
import json


MIN_EXPECTED_VERSION = "0.0.5"
MAX_EXPECTED_VERSION = "0.0.8"
PLUGIN_NAME = "ColorSchemeEditor"
THEME_EDITOR = None
TEMP_FOLDER = "ColorSchemeEditorTemp"
TEMP_PATH = "Packages/User/%s" % TEMP_FOLDER
PLUGIN_SETTINGS = 'color_scheme_editor.sublime-settings'
PREFERENCES = 'Preferences.sublime-settings'
SCHEME = "color_scheme"
THEMES = "theme-list.sublime-settings"

BINARY_PATH = "${Packages}/User/subclrschm"

MIN_VERSION = {
    "osx": MIN_EXPECTED_VERSION,
    "windows": MIN_EXPECTED_VERSION,
    "linux": MIN_EXPECTED_VERSION
}

MAX_VERSION = {
    "osx": MAX_EXPECTED_VERSION,
    "windows": MAX_EXPECTED_VERSION,
    "linux": MAX_EXPECTED_VERSION
}

BINARY = {
    "windows": "subclrschm.exe",
    "osx": "subclrschm.app/Contents/MacOS/subclrschm",
    "linux": "subclrschm"
}

REPO = "https://github.com/facelessuser/subclrschm-bin/archive/%s.zip"

MSGS = {
    "ignore_critical": '''Color Scheme Editor:
You are currently running version %s of subclrschm, %s is the minimum expected version.  Some features may not work. Please consider updating the editor for the best possible experience.

Do you want to ignore this update?
''',

    "ignore": '''Color Scheme Editor:
Do you want to ignore this update?
''',

    "upgrade": '''Color Scheme Editor:
An new version of subclrschm is avalable (%s).

Do you want to update now?
''',

    "linux": '''Color Scheme Editor:
Sorry, currently no love for the penguin. Linux support coming in the future.
''',

    "access": '''Color Scheme Editor:
subclrschm cannot be accessed.
''',

    "binary": '''Color Scheme Editor:
Could not find subclrschm (the editor)!
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
'''
}


def strip_package_ext(pth):
    return pth[:-16] if pth.lower().endswith(".sublime-package") else pth


def sublime_format_path(pth):
    m = re.match(r"^([A-Za-z]{1}):(?:/|\\)(.*)", pth)
    if sublime.platform() == "windows" and m != None:
        pth = m.group(1) + "/" + m.group(2)
    return pth.replace("\\", "/")


def parse_binary_path():
    return normpath(BINARY_PATH).replace("${Packages}", sublime.packages_path())


def nix_check_permissions(bin):
    st = osstat(bin)
    if not bool(st.st_mode & stat.S_IEXEC):
        chmod(bin, st.st_mode | stat.S_IEXEC)


def version_compare(version, min_version):
    cur_v = [int(x) for x in version.split('.')]
    min_v = [int(x) for x in min_version.split('.')]

    return not (
        cur_v[0] < min_v[0] or
        (cur_v[0] == min_v[0] and cur_v[1] < min_v[1]) or
        (cur_v[0] == min_v[0] and cur_v[1] == min_v[1] and cur_v[2] < min_v[2])
    )


def check_version(editor, p_settings, platform):
    version_file = join(parse_binary_path(), "subclrschm-bin-%s" % platform, "version.json")
    try:
        with open(version_file, "r") as f:
            # Allow C style comments and be forgiving of trailing commas
            content = sanitize_json(f.read(), True)
        version = json.loads(content).get("version", None)
    except:
        version = None

    if version is not None:
        # True if versions are okay
        if not version_compare(version, MIN_VERSION[platform]):
            ignore_key = "%s:%s" % (version, MIN_VERSION[platform])
            ignore_versions = str(p_settings.get("ignore_version_update", ""))
            if not ignore_key == ignore_versions:
                if sublime.ok_cancel_dialog(MSGS["upgrade"] % MAX_VERSION[platform], "Update"):
                    sublime.set_timeout(download_package, 100)
                    return
                elif sublime.ok_cancel_dialog(MSGS["ignore_critical"] % (version, MIN_VERSION[platform]), "Ignore"):
                    ignore_versions = ignore_key
                    p_settings.set("ignore_version_update", ignore_versions)
                    sublime.save_settings(PLUGIN_SETTINGS)
        elif not version_compare(version, MAX_VERSION[platform]):
            if sublime.ok_cancel_dialog(MSGS["upgrade"] % MAX_VERSION[platform], "Update"):
                sublime.set_timeout(download_package, 100)
                return
            elif sublime.ok_cancel_dialog(MSGS["ignore_critical"], "Ignore"):
                ignore_key = "%s:%s" % (version, MIN_VERSION[platform])
                ignore_versions = str(p_settings.get("ignore_version_update", ""))
                sublime.save_settings(PLUGIN_SETTINGS)
    else:
        sublime.error_message(MSGS["access"])


def download_package():
    downloaded = False
    binpath = parse_binary_path()
    osbinpath = join(binpath, "subclrschm-bin-%s" % sublime.platform())
    if exists(binpath):
        try:
            if isdir(binpath):
                if exists(osbinpath):
                    shutil.rmtree(osbinpath)
            else:
                remove(binpath)
                makedirs(binpath)

        except Exception as e:
            print(e)
            sublime.error_message("Failed to download")
            return downloaded
    else:
        makedirs(binpath)

    try:
        temp = tempfile.mkdtemp(prefix="subclrschm")
        file_name = join(temp, "subclrschm.zip")
        with request.urlopen(REPO % sublime.platform()) as response, open(file_name, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
        unzip(file_name, binpath)
    except Exception as e:
        print(e)
        sublime.error_message("Failed to download")
        return downloaded
    plugin_loaded()
    if THEME_EDITOR is not None:
        downloaded = True
    return downloaded


def unzip(source, dest_dir):
    with zipfile.ZipFile(source) as z:
        z.extractall(dest_dir)


class ColorSchemeEditorCommand(sublime_plugin.ApplicationCommand):
    def run(self, action=None, select_theme=None):
        if THEME_EDITOR is None:
            if sublime.ok_cancel_dialog(MSGS["download"]):
                if not download_package():
                    return
        # Get current color scheme
        p_settings = sublime.load_settings(PLUGIN_SETTINGS)
        settings = sublime.load_settings(PREFERENCES)
        direct_edit = bool(p_settings.get("direct_edit", False))
        scheme_file = settings.get(SCHEME, None)
        actual_scheme_file = None
        file_select = False

        if action == "select":
            if select_theme is not None:
                scheme_file = select_theme
            else:
                return

        if action != "new" and scheme_file is not None and (action == "current" or action == "select"):
            # Get real path
            actual_scheme_file = join(dirname(sublime.packages_path()), normpath(scheme_file))

            # If scheme cannot be found, it is most likely in an archived package
            if (
                not exists(actual_scheme_file) or
                (not direct_edit and not scheme_file.startswith(TEMP_PATH))
            ):
                # Create temp folder
                zipped_themes = join(sublime.packages_path(), "User", TEMP_FOLDER)
                if not exists(zipped_themes):
                    makedirs(zipped_themes)

                # Read theme file into memory and write out to the temp directory
                text = sublime.load_binary_resource(scheme_file)
                actual_scheme_file = join(zipped_themes, basename(scheme_file))
                try:
                    with open(actual_scheme_file, "wb") as f:
                        f.write(text)
                except:
                    sublime.error_message(MSGS["temp"])
                    return

                # Load unarchived theme
                settings.set(SCHEME, "%s/%s" % (TEMP_PATH, basename(scheme_file)))
            elif action == "select":
                settings.set(SCHEME, scheme_file)
        elif action != "new" and action != "select":
            file_select = True

        if sublime.platform() == "linux":
            nix_check_permissions(THEME_EDITOR)

        # Call the editor with the theme file
        subprocess.Popen(
            [THEME_EDITOR] +
            (["-d"] if bool(p_settings.get("debug", False)) else []) +
            (["-n"] if action == "new" else []) +
            (["-s"] if file_select else []) +
            (["-L"] if bool(p_settings.get("live_edit", True)) else []) +
            ["-l", join(sublime.packages_path(), "User")] +
            # ["--sublime_paths", join(dirname(sublime.executable_path()), 'Packages'), sublime.installed_packages_path(), sublime.packages_path()] +
            ([actual_scheme_file] if actual_scheme_file is not None and exists(actual_scheme_file) else [])
        )


class GetColorSchemeFilesCommand(sublime_plugin.WindowCommand, PackageSearch):
    def on_select(self, value, settings):
        if value != -1:
            preferences = sublime.load_settings(PREFERENCES)
            preferences.set(SCHEME, settings[value])

    def process_file(self, value, settings):
        if value != -1:
            if self.edit:
                sublime.run_command(
                    "color_scheme_editor",
                    {"action": "select", "select_theme": settings[value]}
                )
            else:
                preferences = sublime.load_settings(PREFERENCES)
                preferences.set(SCHEME, scheme_file)
        else:
            if self.current_color_scheme is not None:
                preferences = sublime.load_settings(PREFERENCES)
                preferences.set(SCHEME, self.current_color_scheme)

    def pre_process(self, **kwargs):
        self.edit = kwargs.get("edit", True)
        self.current_color_scheme = sublime.load_settings("Preferences.sublime-settings").get("color_scheme")
        return {"pattern": "*.tmTheme"}

    def run(self, **kwargs):
        self.search(**kwargs)


class ColorSchemeEditorLogCommand(sublime_plugin.WindowCommand):
    def run(self):
        log = join(sublime.packages_path(), "User", "subclrschm.log")
        if exists(log):
            self.window.open_file(log)


class ColorSchemeClearTempCommand(sublime_plugin.ApplicationCommand):
    def run(self):
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


def plugin_loaded():
    global THEME_EDITOR
    platform = sublime.platform()
    p_settings = sublime.load_settings(PLUGIN_SETTINGS)
    p_settings.clear_on_change('reload')

    try:
        # Pick the correct binary for the editor
        THEME_EDITOR = join(parse_binary_path(), "subclrschm-bin-%s" % platform, BINARY[platform])
    except:
        pass

    if THEME_EDITOR is None or not exists(THEME_EDITOR):
        # sublime.error_message(MSGS["binary"])
        THEME_EDITOR = None
    elif platform in ["linux", "osx"]:
        nix_check_permissions(THEME_EDITOR)

    if THEME_EDITOR is not None:
        check_version(THEME_EDITOR, p_settings, platform)

    p_settings.add_on_change('reload', plugin_loaded)

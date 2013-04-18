import sublime
import sublime_plugin
from os.path import join, exists, basename, normpath, dirname, isdir, splitext, isfile
from os import listdir, walk, makedirs, chmod, unlink
from os import stat as osstat
import stat
from fnmatch import fnmatch
import re
import zipfile
import subprocess
import re
import json
import codecs
from plistlib import writePlistToBytes
import urllib.request
import shutil

MIN_EXPECTED_VERSION = "0.0.5"
PLUGIN_NAME = "ColorSchemeEditor"
THEME_EDITOR = None
TEMP_FOLDER = "ColorSchemeEditorTemp"
DOWNLOAD_FOLDER = "ColorSchemeDownloads"
TEMP_PATH = "Packages/User/%s" % TEMP_FOLDER
DOWNLOAD_PATH = "Packages/User/%s" % DOWNLOAD_FOLDER
PLUGIN_SETTINGS = 'color_scheme_editor.sublime-settings'
PREFERENCES = 'Preferences.sublime-settings'
SCHEME = "color_scheme"
THEMES = "theme-list.sublime-settings"
MIN_VERSION = {
    "osx": MIN_EXPECTED_VERSION,
    "windows": MIN_EXPECTED_VERSION,
    "linux": "0.0.0"
}

MSGS = {
    "version": '''Color Scheme Editor:
You are currently running version %s of subclrschm, %s is the minimum expected version.  Some features may not work. Please consider updating the editor for the best possible experience.

Do you want to ignore this update?
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
'''
}


def strip_package_ext(pth):
    return pth[:-16] if pth.lower().endswith(".sublime-package") else pth


def sublime_format_path(pth):
    m = re.match(r"^([A-Za-z]{1}):(?:/|\\)(.*)", pth)
    if sublime.platform() == "windows" and m != None:
        pth = m.group(1) + "/" + m.group(2)
    return pth.replace("\\", "/")


def sublime_package_paths():
    return [sublime.installed_packages_path(), join(dirname(sublime.executable_path()), 'Packages')]


def parse_binary_path(pth):
    return normpath(pth).replace("${Packages}", sublime.packages_path())


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
    p = subprocess.Popen([editor, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out = p.communicate()
    m = re.match(r"subclrschm ([\d]*\.[\d]*\.[\d])*", out[1].decode('utf-8'))
    if m is not None:
        version = m.group(1)
        # True if versions are okay
        if not version_compare(version, MIN_VERSION[platform]):
            ignore_key = "%s:%s" % (version, MIN_VERSION[platform])
            ignore_versions = str(p_settings.get("ignore_version_update", ""))
            if not ignore_key == ignore_versions:
                if sublime.ok_cancel_dialog(MSGS["version"] % (version, MIN_VERSION[platform]), "Ignore"):
                    ignore_versions = ignore_key
                    p_settings.set("ignore_version_update", ignore_versions)
                    sublime.save_settings(PLUGIN_SETTINGS)
    else:
        sublime.error_message(MSGS["access"])


class ColorSchemeEditorCommand(sublime_plugin.ApplicationCommand):
    def run(self, action=None, select_theme=None):
        if THEME_EDITOR is None:
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
            ([actual_scheme_file] if actual_scheme_file is not None and exists(actual_scheme_file) else [])
        )


class RemoveColorSchemeUrlCommand(sublime_plugin.WindowCommand):
    def remove_theme(self, value):
        if value >= 0:
            try:
                shutil.rmtree(self.path[value])
            except:
                sublime.error_message("There was a problem removing %s!" % self.themes[value])

    def hastheme(self, folder):
        has = False
        for f in listdir(folder):
            if isfile(join(folder, f)) and f.lower().endswith(".tmtheme"):
                has = True
                break
        return has

    def run(self):
        self.themes = []
        self.path = []
        download_themes = join(sublime.packages_path(), "User", DOWNLOAD_FOLDER)
        for f in listdir(download_themes):
            full_path = join(download_themes, f)
            if isdir(full_path) and self.hastheme(full_path):
                self.themes.append(f)
                self.path.append(full_path)

        self.window.show_quick_panel(
            self.themes,
            self.remove_theme
        )


class GetColorSchemeUrlCommand(sublime_plugin.WindowCommand):
    def get_theme(self, value):
        if value >= 0:
            name = self.themes[value][0]
            # Create temp folder
            download_themes = join(sublime.packages_path(), "User", DOWNLOAD_FOLDER)
            if not exists(download_themes):
                makedirs(download_themes)

            download_folder = join(download_themes, name)

            if not exists(download_folder):
                makedirs(download_folder)

            url = self.themes[value][1]
            try:
                urllib.request.urlretrieve(url, join(download_folder, urllib.request.url2pathname(basename(url))))
                scheme_file = "Packages/User/%s/%s/%s" % (DOWNLOAD_FOLDER, name, urllib.request.url2pathname(basename(url)))
                if self.edit:
                    sublime.run_command(
                        "color_scheme_editor",
                        {"action": "select", "select_theme": scheme_file}
                    )
                else:
                    preferences = sublime.load_settings(PREFERENCES)
                    preferences.set(SCHEME, scheme_file)
            except:
                sublime.error_message("Could not download %s" % name)

    def run(self, edit=True):
        self.themes = []
        self.edit = edit
        settings = sublime.load_settings(THEMES)
        for t in settings.get("default", []) + settings.get("themes", []):
            self.themes.append([t["name"], t["url"]])

        self.themes.sort(key=lambda l: l[0])

        self.window.show_quick_panel(
            self.themes,
            self.get_theme
        )


class GetColorSchemeFilesCommand(sublime_plugin.WindowCommand):
    theme_files = {"pattern": "*.tmTheme", "regex": False}

    def find_files(self, files, pattern, settings, regex):
        for f in files:
            if regex:
                if re.match(pattern, f[0], re.IGNORECASE) != None:
                    settings.append([f[0].replace(self.packages, "").lstrip("\\").lstrip("/"), f[1]])
            else:
                if fnmatch(f[0], pattern):
                    settings.append([f[0].replace(self.packages, "").lstrip("\\").lstrip("/"), f[1]])

    def walk(self, settings, plugin, pattern, regex=False):
        for base, dirs, files in walk(plugin):
            files = [(join(base, f), "Packages") for f in files]
            self.find_files(files, pattern, settings, regex)

    def load_scheme(self, value, settings):
        if value > -1:
            scheme_file = "Packages/" + settings[value][0].replace("\\", "/")
            if self.edit:
                sublime.run_command(
                    "color_scheme_editor",
                    {"action": "select", "select_theme": scheme_file}
                )
            else:
                preferences = sublime.load_settings(PREFERENCES)
                preferences.set(SCHEME, scheme_file)

    def get_zip_packages(self, file_path, package_type):
        for item in listdir(file_path):
            if fnmatch(item, "*.sublime-package"):
                yield (join(file_path, item), package_type)

    def search_zipped_files(self, unpacked):
        installed = []
        default = []
        st_packages = sublime_package_paths()
        unpacked_path = sublime_format_path(self.packages)
        default_path = sublime_format_path(st_packages[1])
        installed_path = sublime_format_path(st_packages[0])
        for p in self.get_zip_packages(st_packages[0], "Installed"):
            name = strip_package_ext(sublime_format_path(p[0]).replace(installed_path, ""))
            keep = True
            for i in unpacked:
                if name == sublime_format_path(i).replace(unpacked_path, ""):
                    keep = False
                    break
            if keep:
                installed.append(p)

        for p in self.get_zip_packages(st_packages[1], "Default"):
            name = strip_package_ext(sublime_format_path(p[0]).replace(default_path, ""))
            keep = True
            for i in installed:
                if name == strip_package_ext(sublime_format_path(i[0]).replace(installed_path, "")):
                    keep = False
                    break
            for i in unpacked:
                if name == strip_package_ext(sublime_format_path(i[0]).replace(unpacked_path, "")):
                    keep = False
                    break
            if keep:
                default.append(p)
        return sorted(default) + sorted(installed)

    def walk_zip(self, settings, plugin, pattern, regex):
        with zipfile.ZipFile(plugin[0], 'r') as z:
            zipped = [(join(strip_package_ext(basename(plugin[0])), normpath(fn)), plugin[1]) for fn in sorted(z.namelist())]
            self.find_files(zipped, pattern, settings, regex)

    def run(self, edit=True):
        self.edit = edit
        pattern = self.theme_files["pattern"]
        regex = bool(self.theme_files["regex"])
        self.packages = normpath(sublime.packages_path())
        settings = []
        plugins = sorted([join(self.packages, item) for item in listdir(self.packages) if isdir(join(self.packages, item))])
        for plugin in plugins:
            self.walk(settings, plugin, pattern.strip(), regex)

        self.zipped_idx = len(settings)

        zipped_plugins = self.search_zipped_files(plugins)
        for plugin in zipped_plugins:
            self.walk_zip(settings, plugin, pattern.strip(), regex)

        self.window.show_quick_panel(
            settings,
            lambda x: self.load_scheme(x, settings=settings)
        )


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
        if platform == "osx":
            THEME_EDITOR = join(parse_binary_path(p_settings.get("osx")), "Contents", "MacOS", "subclrschm")
        elif platform == "windows":
            THEME_EDITOR = parse_binary_path(p_settings.get("windows"))
        elif platform == "linux":
            THEME_EDITOR = parse_binary_path(p_settings.get("linux"))
            nix_check_permissions(THEME_EDITOR)
    except:
        pass

    if THEME_EDITOR is None or not exists(THEME_EDITOR):
        sublime.error_message(MSGS["binary"])
        THEME_EDITOR = None

    elif THEME_EDITOR is not None:
        check_version(THEME_EDITOR, p_settings, platform)

    p_settings.add_on_change('reload', plugin_loaded)

import sublime
import sublime_plugin
from os.path import join, exists, basename, normpath, dirname
from os import makedirs
import subprocess
import re
import json
import codecs
from plistlib import writePlistToBytes

MIN_EXPECTED_VERSION = "0.0.3"
PLUGIN_NAME = "ColorSchemeEditor"
THEME_EDITOR = None
TEMP_FOLDER = "ColorSchemeEditorTemp"
TEMP_PATH = "Packages/User/%s" % TEMP_FOLDER
PLUGIN_SETTINGS = 'color_scheme_editor.sublime-settings'
PREFERENCES = 'Preferences.sublime-settings'
SCHEME = "color_scheme"
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


class ColorSchemeEditorLogCommand(sublime_plugin.WindowCommand):
    def run(self):
        log = join(sublime.packages_path(), "User", "subclrschm.log")
        if exists(log):
            self.window.open_file(log)


class ColorSchemeEditorCommand(sublime_plugin.ApplicationCommand):
    def run(self, no_direct_edit=True, current_theme=False, new_theme=False):
        if THEME_EDITOR is None:
            return
        # Get current color scheme
        p_settings = sublime.load_settings(PLUGIN_SETTINGS)
        settings = sublime.load_settings(PREFERENCES)
        scheme_file = settings.get(SCHEME, None)
        actual_scheme_file = None
        file_select = False

        if not new_theme and scheme_file is not None and current_theme:
            # Get real path
            actual_scheme_file = join(dirname(sublime.packages_path()), normpath(scheme_file))

            # If scheme cannot be found, it is most likely in an archived package
            if (
                not exists(actual_scheme_file) or
                (no_direct_edit and not scheme_file.startswith(TEMP_PATH))
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
        elif not new_theme:
            file_select = True

        # Call the editor with the theme file
        subprocess.Popen(
            [THEME_EDITOR] +
            (["-d"] if bool(p_settings.get("debug", False)) else []) +
            (["-n"] if new_theme else []) +
            (["-s"] if file_select else []) +
            ["-l", join(sublime.packages_path(), "User")] +
            ([actual_scheme_file] if actual_scheme_file is not None and exists(actual_scheme_file) else [])
        )


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


def parse_binary_path(pth):
    return normpath(pth).replace("${Packages}", sublime.packages_path())


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
            sublime.error_message(MSGS["linux"])
    except:
        pass

    if THEME_EDITOR is None or not exists(THEME_EDITOR):
        sublime.error_message(MSGS["binary"])
        THEME_EDITOR = None

    elif THEME_EDITOR is not None:
        check_version(THEME_EDITOR, p_settings, platform)

    p_settings.add_on_change('reload', plugin_loaded)

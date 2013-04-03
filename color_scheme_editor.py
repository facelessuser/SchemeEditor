import sublime
import sublime_plugin
from os.path import join, exists, basename, normpath, dirname
from os import makedirs
import subprocess

PLUGIN_NAME = "ColorSchemeEditor"
THEME_EDITOR = None
TEMP_FOLDER = "ColorSchemeEditorTemp"
TEMP_PATH = "Packages/User/%s" % TEMP_FOLDER
PLUGIN_SETTINGS = 'color_scheme_editor.sublime-settings'
PREFERENCES = 'Preferences.sublime-settings'
SCHEME = "color_scheme"


class ColorSchemeEditorLogCommand(sublime_plugin.WindowCommand):
    def run(self):
        log = join(sublime.packages_path(), "User", "subclrschm.log")
        if exists(log):
            self.window.open_file(log)


class ColorSchemeEditorCommand(sublime_plugin.ApplicationCommand):
    def run(self, no_direct_edit=True, current_theme=False):
        if THEME_EDITOR is None:
            return
        # Get current color scheme
        p_settigns = sublime.load_settings(PLUGIN_SETTINGS)
        settings = sublime.load_settings(PREFERENCES)
        scheme_file = settings.get(SCHEME, None)
        actual_scheme_file = None


        if scheme_file is not None and current_theme:
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
                    sublime.error_message("Color Scheme Editor:\nCould not copy theme file to temp directory.")
                    return

                # Load unarchived theme
                scheme_file = settings.set(SCHEME, "%s/%s" % (TEMP_PATH, basename(scheme_file)))

        # Call the editor with the theme file
        subprocess.Popen(
            [THEME_EDITOR] +
            (["-d"] if bool(p_settigns.get("debug", False)) else []) +
            ["-l", join(sublime.packages_path(), "User")] +
            ([actual_scheme_file] if actual_scheme_file is not None and exists(actual_scheme_file) else [])
        )


def plugin_loaded():
    global THEME_EDITOR
    platform = sublime.platform()

    # Pick the correct binary for the editor
    if platform == "osx":
        THEME_EDITOR = join(sublime.packages_path(), PLUGIN_NAME, "subclrschm.app", "Contents", "MacOS", "subclrschm")
    elif platform == "windows":
        THEME_EDITOR = join(sublime.packages_path(), PLUGIN_NAME, "subclrschm.exe")
    elif platform == "linux":
        sublime.error_message("Color Scheme Editor:\nSorry, currently no love for the penguin.\nLinux support coming in the future.")

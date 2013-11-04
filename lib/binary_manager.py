# -*- coding: utf-8 -*-
import sublime
import shutil
import tempfile
import urllib.request as request
import zipfile
from os import remove
from .file_strip.json import sanitize_json
import json
from os.path import join, exists, normpath, isdir

UPDATING = False
PLUGIN_SETTINGS = 'color_scheme_editor.sublime-settings'
BINARY_PATH = "${Packages}/User/subclrschm"
MIN_EXPECTED_VERSION = "0.0.5"
MAX_EXPECTED_VERSION = "0.0.8"
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

    "version": '''Color Scheme Editor:
There was a problem comparing versions.
''',

    "install_directory": '''Color Scheme Editor:
Failed trying to create/cleanup folder for subclrschm.  Please make sure subclrschm is not running.
''',

    "install_download": '''Color Scheme Editor:
Failed to download and install subclrschm.
''',

    "install_success": '''Color Scheme Editor:
subclrschm installed!
''',

    "install_busy": '''Color Scheme Editor:
Updater is currently busy attempting an install.
'''
}

STATUS_THROB = "◐◓◑◒"
STATUS_INDEX = 0

def parse_binary_path():
    return normpath(BINARY_PATH).replace("${Packages}", sublime.packages_path())


def get_binary_location():
    platform = sublime.platform()
    return join(parse_binary_path(), "subclrschm-bin-%s" % platform, BINARY[platform])


def version_compare(version, min_version):
    cur_v = [int(x) for x in version.split('.')]
    min_v = [int(x) for x in min_version.split('.')]

    return not (
        cur_v[0] < min_v[0] or
        (cur_v[0] == min_v[0] and cur_v[1] < min_v[1]) or
        (cur_v[0] == min_v[0] and cur_v[1] == min_v[1] and cur_v[2] < min_v[2])
    )


def check_version(editor, p_settings, upgrade_callback):
    update_available = False
    platform = sublime.platform()
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
        ignore_key = "%s:%s" % (version, MAX_VERSION[platform])
        if not version_compare(version, MIN_VERSION[platform]):
            ignore_versions = str(p_settings.get("ignore_version_update", ""))
            if not ignore_key == ignore_versions:
                if sublime.ok_cancel_dialog(MSGS["upgrade"] % MAX_VERSION[platform], "Update"):
                    update_binary(upgrade_callback)
                    update_available = True
                elif sublime.ok_cancel_dialog(MSGS["ignore_critical"] % (version, MIN_VERSION[platform]), "Ignore"):
                    p_settings.set("ignore_version_update", ignore_key)
                    sublime.save_settings(PLUGIN_SETTINGS)
        elif not version_compare(version, MAX_VERSION[platform]):
            if sublime.ok_cancel_dialog(MSGS["upgrade"] % MAX_VERSION[platform], "Update"):
                update_binary(upgrade_callback)
                update_available = True
            elif sublime.ok_cancel_dialog(MSGS["ignore_critical"], "Ignore"):
                p_settings.set("ignore_version_update", ignore_key)
                sublime.save_settings(PLUGIN_SETTINGS)
    else:
        sublime.error_message(MSGS["version"])
    return update_available


def update_binary(callback):
    if not UPDATING:
        sublime.set_timeout_async(lambda: get_binary(callback), 100)
    else:
        sublime.error_message(MSGS["install_busy"])


def update_status():
    global STATUS_INDEX
    if UPDATING:
        if STATUS_INDEX == 3:
            STATUS_INDEX = 0
        else:
            STATUS_INDEX += 1

        sublime.status_message("Installing subclrschm %s" % STATUS_THROB[STATUS_INDEX])
        sublime.set_timeout(update_status, 300)


def get_binary(callback):
    global UPDATING
    UPDATING = True
    sublime.set_timeout(update_status, 300)
    failed = False
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
            failed = True
            sublime.error_message(MSGS["install_directory"])
    else:
        makedirs(binpath)

    if not failed:
        try:
            temp = tempfile.mkdtemp(prefix="subclrschm")
            file_name = join(temp, "subclrschm.zip")
            with request.urlopen(REPO % sublime.platform()) as response, open(file_name, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
            unzip(file_name, binpath)
        except Exception as e:
            print(e)
            failed = True
            sublime.error_message(MSGS["install_download"])

    if not failed:
        sublime.set_timeout(callback, 100)

    UPDATING = False


def binary_upgraded():
    sublime.message_dialog(MSGS["install_success"])
    init_plugin()


def unzip(source, dest_dir):
    with zipfile.ZipFile(source) as z:
        z.extractall(dest_dir)

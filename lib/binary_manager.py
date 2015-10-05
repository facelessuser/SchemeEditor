# -*- coding: utf-8 -*-
from __future__ import absolute_import
import sublime
import shutil
import tempfile
import zipfile
from os import remove, makedirs, rmdir, remove
from .file_strip.json import sanitize_json
import json
from os.path import join, exists, normpath, isdir
import threading

ST3 = int(sublime.version()) >= 3000
if ST3:
    import urllib.request
else:
    import urllib2
LOCK = threading.Lock()
UPDATING = False
PLUGIN_SETTINGS = 'color_scheme_editor.sublime-settings'
BINARY_PATH = "${Packages}/User/subclrschm"
BINARY = {
    "windows": "subclrschm.exe",
    "osx": "subclrschm.app/Contents/MacOS/subclrschm",
    "linux": "subclrschm"
}
REPO = "https://github.com/facelessuser/subclrschm-bin/archive/%s.zip"
MSGS = {
    "ignore_critical": '''Color Scheme Editor:
You are currently running version %s of subclrschm, %s is outdated.  Some features may not work. Please consider updating the editor for the best possible experience.

Do you want to hide this message for this version in the future?
''',

    "ignore": '''Color Scheme Editor:
Do you want to ignore this update?
''',

    "upgrade": '''Color Scheme Editor:
A new version of subclrschm is avalable (%s).

Do you want to update now?
''',

    "version": '''Color Scheme Editor:
There was a problem comparing versions.
'''
}

if ST3:
    STATUS_THROB = "◐◓◑◒"
else:
    STATUS_THROB = "-\\|/"
STATUS_INDEX = 0


def on_rm_error(func, path, exc_info):
    excvalue = exc_info[1]
    if func in (rmdir, remove):
        chmod(path, stat.S_IRWXU| stat.S_IRWXG| stat.S_IRWXO) # 0777
        try:
            func(path)
        except:
            if sublime.platform() == "windows":
                # Why are you being so stubborn windows?
                # This situation only randomly occurs
                print("Windows is being stubborn...go through rmdir to remove temp folder")
                import subprocess
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
                    print("Why won't you play nice, Windows!")
                    print(process.communicate()[0])
                    raise
            else:
                raise
    else:
        raise


def load_resource(resource, binary=False):
    bfr = None
    if ST3:
        if not binary:
            bfr = sublime.load_resource(resource)
        else:
            bfr = sublime.load_binary_resource(resource)
    else:
        resource = resource.replace("Packages/", "", 1)
        if sublime.platform() == "windows":
            resource = resource.replace("/", "\\")
        try:
            mode = "rb" if binary else "r"
            with open(join(sublime.packages_path(), resource), mode) as f:
                bfr = f.read()
        except Exception as e:
            print(e)
    return bfr


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


def read_versions():
    platform = sublime.platform()
    version_file = join(parse_binary_path(), "subclrschm-bin-%s" % platform, "version.json")
    try:
        with open(version_file, "r") as f:
            # Allow C style comments and be forgiving of trailing commas
            content = sanitize_json(f.read(), True)
        version = json.loads(content).get("version", None)
        content = sanitize_json(
            load_resource("Packages/ColorSchemeEditor/version.json"),
            True
        )
        version_limits = json.loads(content).get(platform, None)
        if (
            version_limits is None or
            version_limits.get("min", None) is None or
            version_limits.get("max", None) is None
        ):
            version_limits = None
    except Exception as e:
        print(e)
        version_limits = None
        version = None
    return version, version_limits


def check_version(editor, p_settings, upgrade_callback):
    """Check version of old binary."""

    update_available = False
    version, version_limits = read_versions()

    if version is not None and version_limits is not None:
        # True if versions are okay
        ignore_key = "%s:%s" % (version, version_limits["max"])
        if not version_compare(version, version_limits["min"]):
            ignore_versions = str(p_settings.get("ignore_version_update", ""))
            if not ignore_key == ignore_versions:

                if sublime.ok_cancel_dialog(MSGS["ignore_critical"] % (version, version_limits["min"]), "Ignore"):
                    p_settings.set("ignore_version_update", ignore_key)
                    sublime.save_settings(PLUGIN_SETTINGS)

        elif not version_compare(version, version_limits["max"]):
            if sublime.ok_cancel_dialog(MSGS["ignore_critical"] % (version, version_limits["max"]), "Ignore"):
                p_settings.set("ignore_version_update", ignore_key)
                sublime.save_settings(PLUGIN_SETTINGS)
    # If version cannot be found, we don't care as this is the legacy method.

    return update_available


def delete_old_binary(self):
    """Delete old binary."""

    binpath = parse_binary_path()
    osbinpath = join(binpath, "subclrschm-bin-%s" % sublime.platform())
    try:
        if exists(binpath):
            if isdir(binpath):
                if exists(osbinpath):
                    shutil.rmtree(osbinpath, onerror=on_rm_error)
            else:
                remove(binpath)
    except Exception as e:
        print(e)

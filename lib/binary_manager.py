# -*- coding: utf-8 -*-
from __future__ import absolute_import
import sublime
import shutil
import tempfile
import zipfile
from os import remove, makedirs
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

if ST3:
    STATUS_THROB = "◐◓◑◒"
else:
    STATUS_THROB = "-\\|/"
STATUS_INDEX = 0


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
    update_available = False
    version, version_limits = read_versions()

    if version is not None and version_limits is not None:
        # True if versions are okay
        ignore_key = "%s:%s" % (version, version_limits["max"])
        if not version_compare(version, version_limits["min"]):
            ignore_versions = str(p_settings.get("ignore_version_update", ""))
            if not ignore_key == ignore_versions:
                if sublime.ok_cancel_dialog(MSGS["upgrade"] % version_limits["max"], "Update"):
                    update_binary(upgrade_callback)
                    update_available = True
                elif sublime.ok_cancel_dialog(MSGS["ignore_critical"] % (version, version_limits["min"]), "Ignore"):
                    p_settings.set("ignore_version_update", ignore_key)
                    sublime.save_settings(PLUGIN_SETTINGS)

        elif not version_compare(version, version_limits["max"]):
            if sublime.ok_cancel_dialog(MSGS["upgrade"] % version_limits["max"], "Update"):
                update_binary(upgrade_callback)
                update_available = True
            elif sublime.ok_cancel_dialog(MSGS["ignore_critical"], "Ignore"):
                p_settings.set("ignore_version_update", ignore_key)
                sublime.save_settings(PLUGIN_SETTINGS)
    else:
        sublime.error_message(MSGS["version"])
    return update_available


def update_binary(callback):
    with LOCK:
        updating = UPDATING

    if not updating:
        t = GetBinary()
        t.start()
        MonitorThread(t, callback)
    else:
        sublime.error_message(MSGS["install_busy"])


class MonitorThread():
    def __init__(self, t, callback):
        self.callback = callback
        self.thread = t
        sublime.set_timeout(lambda: self.__start_monitor(), 0)

    def __throb(self):
        global STATUS_INDEX
        with LOCK:
            if STATUS_INDEX == 3:
                STATUS_INDEX = 0
            else:
                STATUS_INDEX += 1

        sublime.status_message("Installing subclrschm %s" % STATUS_THROB[STATUS_INDEX])

    def __start_monitor(self):
        self.__throb()
        sublime.set_timeout(lambda: self.__monitor(), 300)

    def __monitor(self):
        self.__throb()
        if self.thread.is_alive():
            sublime.set_timeout(self.__monitor, 300)
        else:
            if self.thread.error_message is not None:
                sublime.set_timeout(lambda: sublime.error_message(self.thread.error_message), 100)
            else:
                sublime.set_timeout(lambda: binary_upgraded(self.callback), 100)


class GetBinary(threading.Thread):
    error_message = None

    def __init__(self):
        threading.Thread.__init__(self)

    def prepare_destination(self, binpath):
        osbinpath = join(binpath, "subclrschm-bin-%s" % sublime.platform())
        try:
            if exists(binpath):
                if isdir(binpath):
                    if exists(osbinpath):
                        shutil.rmtree(osbinpath)
                else:
                    remove(binpath)
                    makedirs(binpath)
            else:
                makedirs(binpath)
        except Exception as e:
            print(e)
            self.error_message = MSGS["install_directory"]

    def download_file(self, url, destination):
        if ST3:
            with urllib.request.urlopen(url) as response:
                with open(destination, 'wb') as out_file:
                    shutil.copyfileobj(response, out_file)
        else:
            req = urllib2.Request(url)
            response = urllib2.urlopen(req)
            with open(destination, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
            response.close()

    def get_binary(self):
        binpath = parse_binary_path()
        self.prepare_destination(binpath)
        if self.error_message is None:
            try:
                temp = tempfile.mkdtemp(prefix="subclrschm")
                file_name = join(temp, "subclrschm.zip")
                self.download_file(REPO % sublime.platform(), file_name)
                unzip(file_name, binpath)
                if exists(temp):
                    shutil.rmtree(temp)
            except Exception as e:
                print(e)
                self.error_message = MSGS["install_download"]

    def run(self):
        global UPDATING
        with LOCK:
            UPDATING = True
        self.get_binary()
        with LOCK:
            UPDATING = False


def binary_upgraded(callback):
    sublime.message_dialog(MSGS["install_success"])
    callback()


def unzip(source, dest_dir):
    if ST3:
        with zipfile.ZipFile(source) as z:
            z.extractall(dest_dir)
    else:
        z = zipfile.ZipFile(source)
        z.extractall(dest_dir)
        z.close()

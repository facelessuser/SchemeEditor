"""
Submlime Text Package File Search
Licensed under MIT
Copyright (c) 2012 Isaac Muse <isaacmuse@gmail.com>
"""
import sublime
import re
from os import walk, listdir
from os.path import basename, dirname, isdir, join, normpath
from fnmatch import fnmatch
import zipfile


def sublime_package_paths():
    return [sublime.installed_packages_path(), join(dirname(sublime.executable_path()), 'Packages')]


class PackageSearch(object):
    def pre_process(self, **kwargs):
        return kwargs

    def on_select(self, value, settings):
        pass

    def process_file(self, value, settings):
        pass

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

    def get_zip_packages(self, file_path, package_type):
        plugins = [(join(file_path, item), package_type) for item in listdir(file_path) if fnmatch(item, "*.sublime-package")]
        return plugins

    def search_zipped_files(self):
        plugins = []
        st_packages = sublime_package_paths()
        plugins += self.get_zip_packages(st_packages[0], "Installed")
        plugins += self.get_zip_packages(st_packages[1], "Default")
        return plugins

    def walk_zip(self, settings, plugin, pattern, regex):
        with zipfile.ZipFile(plugin[0], 'r') as z:
            zipped = [(join(basename(plugin[0]), normpath(fn)), plugin[1]) for fn in sorted(z.namelist())]
            self.find_files(zipped, pattern, settings, regex)

    def find_raw(self, pattern, regex=False):
        self.packages = normpath(sublime.packages_path())
        settings = []
        plugins = [join(self.packages, item) for item in listdir(self.packages) if isdir(join(self.packages, item))]
        for plugin in plugins:
            self.walk(settings, plugin, pattern.strip(), regex)

        self.zipped_idx = len(settings)

        zipped_plugins = self.search_zipped_files()
        for plugin in zipped_plugins:
            self.walk_zip(settings, plugin, pattern.strip(), regex)

        self.window.show_quick_panel(
            settings,
            lambda x: self.process_file(x, settings=settings)
        )

    def find(self, pattern, regex):
        resources = []
        if not regex:
            resources = sublime.find_resources(pattern)
        else:
            temp = sublime.find_resources("*")
            for t in temp:
                if re.match(pattern, t, re.IGNORECASE) != None:
                    resources.append(t)

        self.window.show_quick_panel(
            resources,
            lambda x: self.process_file(x, settings=resources),
            0,
            0,
            lambda x: self.on_select(x, settings=resources)
        )

    def search(self, **kwargs):
        kwargs = self.pre_process(**kwargs)
        pattern = kwargs.get("pattern", None)
        regex = kwargs.get("regex", False)
        self.find_all = kwargs.get("find_all", False)

        if not self.find_all:
            self.find(pattern, regex)
        else:
            self.find_raw(pattern, regex)

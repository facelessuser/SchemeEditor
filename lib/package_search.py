"""
Submlime Text Package File Search.

Licensed under MIT
Copyright (c) 2012 Isaac Muse <isaacmuse@gmail.com>
"""
import sublime
import re
from os import walk, listdir
from os.path import basename, dirname, isdir, join, normpath, splitext, exists
from fnmatch import fnmatch
import zipfile

__all__ = (
    "sublime_package_paths",
    "scan_for_packages",
    "packagename",
    "get_packages",
    "get_packages_location",
    "get_package_contents",
    "PackageSearch"
)

EXCLUDE_PATTERN = re.compile(r"(?:/|^)(?:[^/]*\.(?:pyc|pyo)|\.git|\.svn|\.hg|\.DS_Store)(?=$|/)")


def sublime_package_paths():
    """Get all the locations where plugins live."""

    return [
        sublime.installed_packages_path(),
        join(dirname(sublime.executable_path()), "Packages"),
        sublime.packages_path()
    ]


def scan_for_packages(file_path, archives=False):
    """Look for zipped and unzipped plugins."""

    if archives:
        plugins = [join(file_path, item) for item in listdir(file_path) if fnmatch(item, "*.sublime-package")]
    else:
        plugins = [join(file_path, item) for item in listdir(file_path) if isdir(join(file_path, item))]

    return plugins


def packagename(pth, normalize=False):
    """Get the package name from the path."""

    if isdir(pth):
        name = basename(pth)
    else:
        name = splitext(basename(pth))[0]
    return name.lower() if sublime.platform() == "windows" and normalize else name


def get_packages_location():
    """Get all packages.  Optionally disable resolving override packages."""

    installed_pth, default_pth, user_pth = sublime_package_paths()

    installed_pkgs = scan_for_packages(installed_pth, archives=True)
    default_pkgs = scan_for_packages(default_pth, archives=True)
    user_pkgs = scan_for_packages(user_pth)

    return default_pkgs, installed_pkgs, user_pkgs


def get_folder_resources(folder_pkg, pkg_name, content_folders, content_files):
    """Get resources in folder."""

    if exists(folder_pkg):
        for base, dirs, files in walk(folder_pkg):
            file_objs = []
            for d in dirs[:]:
                if EXCLUDE_PATTERN.search(d) is not None:
                    dirs.remove(d)
            for f in files:
                if EXCLUDE_PATTERN.search(f) is None:
                    file_name = join(base, f).replace(folder_pkg, "Packages/%s" % pkg_name, 1).replace("\\", "/")
                    file_objs.append(file_name)
                    content_files.append(file_name)
            if len(file_objs) == 0 and len(dirs) == 0:
                content_folders.append(base.replace(folder_pkg, "Packages/%s" % pkg_name, 1).replace("\\", "/") + "/")


def in_list(x, l):
    """Find if x (string) is in l (list)."""

    found = False
    if sublime.platform() == "windows":
        for item in l:
            if item.lower() == x.lower():
                found = True
                break
    else:
        found = x in l
    return found


def get_zip_resources(zip_pkg, pkg_name, content_folders, content_files):
    """Get resources in archive that are not already in the lists."""

    if exists(zip_pkg):
        with zipfile.ZipFile(zip_pkg, 'r') as z:
            for item in z.infolist():
                file_name = item.filename
                if EXCLUDE_PATTERN.search(file_name) is None:
                    package_name = "Packages/%s/%s" % (pkg_name, file_name)
                    if package_name.endswith('/'):
                        if not in_list(package_name, content_folders):
                            content_folders.append(package_name)
                    elif not package_name.endswith('/'):
                        if not in_list(package_name, content_files):
                            content_files.append(package_name)


def get_package_contents(pkg):
    """Get contents of package."""

    m = re.match(r"^Packages/([^/]*)/?$", pkg)
    assert(m is not None)
    pkg = m.group(1)
    installed_pth, default_pth, user_pth = sublime_package_paths()
    content_files = []
    content_folders = []

    get_folder_resources(join(user_pth, pkg), pkg, content_folders, content_files)
    get_zip_resources(join(installed_pth, "%s.sublime-package" % pkg), pkg, content_folders, content_files)
    get_zip_resources(join(default_pth, "%s.sublime-package" % pkg), pkg, content_folders, content_files)

    return content_folders + content_files


def get_packages():
    """Get the package names."""

    installed_pth, default_pth, user_pth = sublime_package_paths()

    installed_pkgs = scan_for_packages(installed_pth, archives=True)
    default_pkgs = scan_for_packages(default_pth, archives=True)
    user_pkgs = scan_for_packages(user_pth)

    pkgs = []
    for pkg_type in [user_pkgs, installed_pkgs, default_pkgs]:
        for pkg in pkg_type:
            name = packagename(pkg)
            if not in_list(name, pkgs):
                pkgs.append(name)

    pkgs.sort()

    return pkgs


class PackageSearch(object):
    """Search packages."""

    def pre_process(self, **kwargs):
        """Preprocess event."""

        return kwargs

    def on_select(self, value, settings):
        """On select event."""

    def process_file(self, value, settings):
        """Handle processing the file."""

    ################
    # Qualify Files
    ################
    def find_files(self, files, file_path, pattern, settings, regex):
        """Find the file that matches the pattern."""

        for f in files:
            if regex:
                if re.match(pattern, f[0], re.IGNORECASE) is not None:
                    settings.append([f[0].replace(file_path, "").lstrip("\\").lstrip("/"), f[1]])
            else:
                if fnmatch(f[0], pattern):
                    settings.append([f[0].replace(file_path, "").lstrip("\\").lstrip("/"), f[1]])

    ################
    # Zipped
    ################
    def walk_zip(self, settings, plugin, pattern, regex):
        """Walk the archived files within the plugin."""

        with zipfile.ZipFile(plugin[0], 'r') as z:
            zipped = [(join(basename(plugin[0]), normpath(fn)), plugin[1]) for fn in sorted(z.namelist())]
            self.find_files(zipped, "", pattern, settings, regex)

    def get_zip_packages(self, settings, file_path, package_type, pattern, regex=False):
        """Get all the archived plugins in the plugin folder."""

        plugins = [
            (join(file_path, item), package_type) for item in listdir(file_path) if fnmatch(item, "*.sublime-package")
        ]
        for plugin in plugins:
            self.walk_zip(settings, plugin, pattern.strip(), regex)

    def search_zipped_files(self, settings, pattern, regex):
        """Search the plugin folders for archived plugins."""

        st_packages = sublime_package_paths()
        self.get_zip_packages(settings, st_packages[0], "Installed", pattern, regex)
        self.get_zip_packages(settings, st_packages[1], "Default", pattern, regex)

    ################
    # Unzipped
    ################
    def walk(self, settings, file_path, plugin, package_type, pattern, regex=False):
        """Walk the files within the plugin."""

        for base, dirs, files in walk(plugin):
            files = [(join(base, f), package_type) for f in files]
            self.find_files(files, file_path, pattern, settings, regex)

    def get_unzipped_packages(self, settings, file_path, package_type, pattern, regex=False):
        """Get all of the plugins in the plugin folder."""

        plugins = [join(file_path, item) for item in listdir(file_path) if isdir(join(file_path, item))]
        for plugin in plugins:
            self.walk(settings, file_path, plugin, package_type, pattern.strip(), regex)

    def search_unzipped_files(self, settings, pattern, regex):
        """Search the plugin folders for unzipped packages."""

        st_packages = sublime_package_paths()
        self.get_unzipped_packages(settings, st_packages[2], "Packages", pattern, regex)

    ################
    # Search All
    ################
    def find_raw(self, pattern, regex=False):
        """Search all packages regardless of whether it is being overridden."""

        settings = []
        self.search_unzipped_files(settings, pattern, regex)
        self.zipped_idx = len(settings)
        self.search_zipped_files(settings, pattern, regex)

        self.window.show_quick_panel(
            settings,
            lambda x: self.process_file(x, settings=settings)
        )

    ################
    # Search Override
    ################
    def find(self, pattern, regex):
        """Search just the active packages.  Not the ones that have been overridden."""

        resources = []
        if not regex:
            resources = sublime.find_resources(pattern)
        else:
            temp = sublime.find_resources("*")
            for t in temp:
                if re.match(pattern, t, re.IGNORECASE) is not None:
                    resources.append(t)

        self.window.show_quick_panel(
            resources,
            lambda x: self.process_file(x, settings=resources),
            0,
            0,
            lambda x: self.on_select(x, settings=resources)
        )

    def search(self, **kwargs):
        """Search packages."""

        kwargs = self.pre_process(**kwargs)
        pattern = kwargs.get("pattern", None)
        regex = kwargs.get("regex", False)
        self.find_all = kwargs.get("find_all", False)

        if not self.find_all:
            self.find(pattern, regex)
        else:
            self.find_raw(pattern, regex)

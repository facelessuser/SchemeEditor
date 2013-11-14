'''
Favorite Files
Licensed under MIT
Copyright (c) 2012 Isaac Muse <isaacmuse@gmail.com>
'''

import re


def _strip_regex(pattern, text, preserve_lines):
    def remove_comments(group, preserve_lines=False):
        return ''.join([x[0] for x in re.compile(r"\r?\n", re.MULTILINE).findall(group)]) if preserve_lines else ''

    return (
        ''.join(
            map(
                lambda m: m.group(2) if m.group(2) else remove_comments(m.group(1), preserve_lines),
                re.compile(pattern, re.MULTILINE | re.DOTALL).finditer(text)
            )
        )
    )


def _cpp(self, text, preserve_lines=False):
    return _strip_regex(
        r"""(/\*[^*]*\*+(?:[^/*][^*]*\*+)*/|\s*//(?:[^\r\n])*)|("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|.[^/"']*)""",
        text,
        preserve_lines
    )


def _python(self, text, preserve_lines=False):
    return _strip_regex(
        r"""(\s*#(?:[^\r\n])*)|("{3}(?:\\.|[^\\])*"{3}|'{3}(?:\\.|[^\\])*'{3}|"(?:\\.|[^"\\])*"|'(?:\\.|[^'])*'|.[^#"']*)""",
        text,
        preserve_lines
    )


class CommentException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class Comments(object):
    styles = []

    def __init__(self, style=None, preserve_lines=False):
        self.preserve_lines = preserve_lines
        self.call = self.__get_style(style)

    @classmethod
    def add_style(cls, style, fn):
        if not style in cls.__dict__:
            setattr(cls, style, fn)
            cls.styles.append(style)

    def __get_style(self, style):
        if style in self.styles:
            return getattr(self, style)
        else:
            raise CommentException(style)

    def strip(self, text):
        return self.call(text, self.preserve_lines)

Comments.add_style("c", _cpp)
Comments.add_style("json", _cpp)
Comments.add_style("cpp", _cpp)
Comments.add_style("python", _python)

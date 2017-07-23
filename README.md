SchemeEditor
=================

Sublime Color Scheme Editor for Sublime Text

## Supported Platforms

Windows

![Windows](https://github.com/facelessuser/subclrschm/blob/master/docs/src/markdown/images/CSE_WIN.png)

macOS

![macOS](https://github.com/facelessuser/subclrschm/blob/master/docs/src/markdown/images/CSE_OSX.png)

Linux

![Linux](https://github.com/facelessuser/subclrschm/blob/master/docs/src/markdown/images/CSE_NIX.png

## Installation

- Install this package in your Sublime `Packages` folder.
- Pip install [subclrschm](https://pypi.python.org/pypi/subclrschm/) version 2.0.2+ in your local Python installation.
- Configure your `scheme_editor.sublime-settings` file to call `subclrschm`.

    ```js
    // Path of subclrschm app
    // Just setup call to the app. No need to setup app options as that is controlled
    // by the plugin.
    "editor": {
        "windows": ["python", "-m", "subclrschm"],
        "osx": ["python", "-m", "subclrschm"],
        "linux": ["python", "-m", "subclrschm"]
    }
    ```

## Optional Settings

```js
    // Enable or disable live editing
    // (live editing saves to the file right after changes are made)
    // This is not enabled by default for open with file picker and new themes
    "live_edit": true,

    // Enable or disable direct editing
    // All files are copied to a temp location before editing.
    // If direct edit is enabled, the file will be edited directly
    // except in cases where the theme file is inside a sublime-packages
    // archive
    "direct_edit": false,
```

## Usage

All commands are available via the command palette.  Here are the included commands:

```js
    // Open the current theme in the editor
    // (copy to separate location first and set to current theme)
    {
        "caption": "SchemeEditor: Edit Scheme (file picker)",
        "command": "scheme_editor",
        "args": { "live_edit": false }
    },
    // Creates a new theme in the editor
    // (copy to separate location first and set to current theme)
    {
        "caption": "SchemeEditor: Create New Scheme",
        "command": "scheme_editor",
        "args": { "action": "new", "live_edit": false }
    },
    // Open the current theme in the editor
    // (copy to separate location first and set to current theme)
    {
        "caption": "SchemeEditor: Edit Current Scheme",
        "command": "scheme_editor",
        "args": { "action": "current" }
    },
    // Search plugins for themes and choose one to edit
    {
        "caption": "SchemeEditor: Edit installed scheme",
        "command": "scheme_editor_get_scheme"
    },
    // Open log file in Sublime Text
    {
        "caption": "SchemeEditor: Get Editor Log",
        "command": "scheme_editor_log"
    },
    // Clear Temp Folder
    {
        "caption": "SchemeEditor: Clear Temp Folder",
        "command": "scheme_clear_temp"
    }
```

## Questions

*How can I get undefined scopes into the editor?*

ScopeHunter is a plugin I wrote that you can configure to put the scope of what is under the cursor into your clipboard (it also can show you a lot of other stuff, but you configure it how you want it to work). So you can use that to quickly get the scope into your clipboard, then you can open up the scheme editor.

The SublimeText3 documentation has a page on scope naming: http://www.sublimetext.com/docs/3/scope_naming.html.

## License
SchemeEditor plugin is released under the MIT license.

Copyright (c) 2013 - 2017 Isaac Muse <isaacmuse@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

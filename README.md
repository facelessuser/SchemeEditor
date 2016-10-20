ColorSchemeEditor
=================

Color Scheme Editor for Sublime Text

# Usage

This is a color scheme editor (tmTheme file editor) for Sublime Text (only tested on ST3 so far). The editor live edits your theme file so you can watch the colors change in your editor.

It consists of two parts: a Sublime Text package, and a GUI which makes visual editing of tmTheme files easier.

To protect against unwanted changes, the theme file is copied over to a temp directory (```User/ColorSchemeEditorTemp```), and set as your default theme before opening in the editor. If you would like to edit the original directly (as long as it is not inside a sublime-package archive), this can be disabled, and the editor will edit the theme file directly. When it saves the tmTheme file, it will also create a ```tmTheme.JSON``` file as well.

Transparent colors are also supported, but built in color pickers on systems don't usually have alpha support, so you have to add the alpha byte on manually via the text box. The editor will simulate how sublime will display the transparency color for you inside the editor.

* Delete Record: press the <kbd>delete</kbd> key when selecting a row
* Insert Record: press <kbd>CMD + </kbd> OSX or <kbd>CTRL + i</kbd> Win/Linux
* Move Setting (not for global settings): <kbd>alt + up</kbd>   or <kbd>alt + down</kbd>
* Edit Item: **double left click**  or <kbd>enter</kbd>

See http://www.sublimetext.com/forum/viewtopic.php?f=5&t=11819 for more information, including feature requests, bug reports and a rough roadmap for development. That will be updated more frequently than this ReadMe.

# Supported Platforms
## Windows
<img src="https://dl.dropboxusercontent.com/u/342698/ColorSchemeEditor/CSE_WIN.png" border="0"/>

## OSX
<img src="https://dl.dropboxusercontent.com/u/342698/ColorSchemeEditor/CSE_OSX.png" border="0"/>

## Ubuntu 12.10 32 Bit
<img src="https://dl.dropboxusercontent.com/u/342698/ColorSchemeEditor/CSE_NIX.png" border="0"/>

# Installation

* Install the [plugin from github](github.com/facelessuser/ColorSchemeEditor) (binaries for editor not included) or via Package Control
* **Download the binary** for your platform below and place it on your computer 
 * The plugin is setup to look in your User folder, but you can change that in the settings file of the plugin to look elsewhere if desired
* Commands are available in the command palette

A more comprehensive guide including information about building from source is at <http://mattdmo.com/guide-to-installing-colorschemeeditor-for-sublime-text-3/>

## Binaries

Download: [Windows 0.0.8](https://dl.dropboxusercontent.com/u/342698/ColorSchemeEditor/subclrschm_win_0.0.8.zip)
  
Download: [OSX 0.0.8](https://dl.dropboxusercontent.com/u/342698/ColorSchemeEditor/subclrschm_osx_0.0.8.zip)
  
Download: [Ubuntu 12.10 32 Bit 0.0.8](https://dl.dropboxusercontent.com/u/342698/ColorSchemeEditor/subclrschm_UBU_0.0.8.zip)

Source code for the GUI is found [here](https://github.com/facelessuser/subclrschm).

# Questions:

_Why are the binaries so big?_  

Binaries are larger than you would think needed for this because these are python code compiled into binaries. They contain what they need from python so you don't have to have python installed on your system. Binaries on some platforms will be larger than others.

_How can I get undefined scopes in to the editor?_

[ScopeHunter](https://github.com/facelessuser/ScopeHunter) is a plugin I wrote that you can configure to put the scope of what is under the cursor into your clipboard (it also can show you a lot of other stuff, but you configure it how you want it to work). So you can use that to quickly get the scope into your clipboard, then you can open up the scheme editor.

@alehandrof created some lists of scopes https://gist.github.com/alehandrof/5361546

The SublimeText3 documentation has a page on scope naming http://www.sublimetext.com/docs/3/scope_naming.html


# License
ColorSchemeEditor plugin is released under the MIT license.

Copyright (c) 2013 Isaac Muse <isaacmuse@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# ENSIME Sublime

[![Join the chat at https://gitter.im/ensime/ensime-sublime](https://badges.gitter.im/Join%20Chat.svg)](https://gitter.im/ensime/ensime-sublime?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

ENSIME Sublime provides Scala support to Sublime Text 3.

The project is in active development.
Watch this space for news and improvements,
and submit issues to [our tracker](https://github.com/ensime/ensime-sublime/issues/new).

Note: Sublime Text 2 support is deprecated.
All active development is happening for Sublime Text 3.
If you are interest in Sublime Text 2 support, consider contributing to the
[Sublime Text 2 Branch](https://github.com/ensime/ensime-sublime/tree/ST2).

## Project status

The project is up and functional and supports a subset of the ENSIME features:

* error highlighting
* code completion (hit `.` followed by `ctrl-space` or `command-space`)
* goto definition
* type hints
* extract local, extract method
* add import, organize imports
* supports Scala 2.10 and 2.11

## Getting it going

[Installation Instructions](http://ensime.github.io/editors/sublime/installation/ "Installation Instructions")

## What Does ENSIME Sublime Do?

Once you have run the *"Ensime: Startup"* command,
ENSIME Sublime will enrich your Scala experience with the following features:

- Syntax highlighting
  - Highlighting is semantic rather than regex-based.
  - If you make a mistake, it is outlined in red.

- Mouse commands
  - Right-clicking yields useful context menu items.
  - `Ctrl-Click` or `Cmd-Click` invokes *Go to Definition*.
  - `Alt-Click` invokes *Inspect Type at Point*.

- Keyboard
  - Typing `Ctrl-Space` will show an autocomplete menu.
  - Other keybindings can be added via keymaps (see below).

## Additional Configuration

### Line Endings (Windows Users)

Windows users should ensure the `Line Endings` setting is set to `Unix`.
Go to *View Menu / Line Endings* and select *Unix*.

### Mouse Clicks

ENSIME Sublime customizes mouse bindings.
It makes `Ctrl+Click`/`Cmd+Click` invoke `Go to Definition`
and `Alt+Click` stand for `Inspect Type at Point`.

These bindings can be altered in the the config:
*Preferences Menu / Package Settings / Ensime / Mousemap - Default*.

### Key Bindings

`Ctrl+Space` invokes code completion by default.

Other keybindings can be enabled in the config:
*Preferences Menu / Package Settings / Ensime / Keymap - Default*.

## Troubleshooting

### Checking Java and SBT Visiblity

Unsure whether Sublime Text can see Java and SBT on your system application path?
Try pasting the following commands one at a time into the Sublime Text console
(*View menu / Show Console*).

On Linux or OS X:

~~~ python
# Check the visibility of Java:
import subprocess; print(subprocess.check_output(['which', 'java'], stderr=subprocess.STDOUT).decode("utf-8"))

# Check the visibility of SBT:
import subprocess; print(subprocess.check_output(['which', 'sbt'], stderr=subprocess.STDOUT).decode("utf-8"))
~~~

On Windows:

~~~ python
# Check the visibility of Java:
import subprocess; print(subprocess.check_output(['where', 'java'], stderr=subprocess.STDOUT).decode("utf-8"))

# Check the visibility of SBT:
import subprocess; print(subprocess.check_output(['where', 'sbt'], stderr=subprocess.STDOUT).decode("utf-8"))
~~~

In each case you should see a path string, something like this:

~~~
b'/usr/bin/java\n'
~~~

If you see and error message like this, Sublime Text can't see the relevant executable:

~~~
Traceback (most recent call last):
  File "<string>", line 1, in <module>
  File "./subprocess.py", line 589, in check_output
subprocess.CalledProcessError: Command '['which', 'java']' returned non-zero exit status 1
~~~

### Checking Java and SBT Versions

Ideally you should be using Java 8 and SBT 0.13.x.
To check this, paste the following commands one at a time into the console
(*View Menu / Show Console*):

~~~ python
# Check the Java version:
import subprocess; print(subprocess.check_output(['java', '-version'], stderr=subprocess.STDOUT).decode("utf-8"))

# Check the SBT version:
import subprocess; print(subprocess.check_output(['sbt', 'sbtVersion'], stderr=subprocess.STDOUT).decode("utf-8"))
~~~

### No Commands in the Command Palette?

If your command palette doesn't contain the *Ensime: Startup* menu item,
it is most likely because ENSIME Sublime can't find your `.ensime` file:

- Ensure you have created a `.ensime` file using the `gen-ensime` command.

  If you have recently (re)generated your `.ensime` file,
  you may have to quit and restart Sublime Text to pick up the changes.

- Ensure the top-most item in the Side Bar (*View Menu / Side Bar / Show Side Bar*)
  is your project directory (the one containing the `.ensime` file).

  If not, choose *File Menu / Open...* and open the project directory directly.

### Line Endings

If you find that some features of Ensime are not working properly
(e.g. *Go To Definition* or *Error Highlighting*), check the *Line Endings* setting in Sublime Text.

On Windows, the line endings is set to *Windows* by default. ENSIME Sublime requires it to be *Unix*.
Change the setting by going to *View menu / Line Endings* and selecting *Unix*.

Also check *View menu / Console* for log information.

## Tips for ENSIME Developers

If you are hacking on ENSIME Sublime, there are a few things you may want to do differently.

### Installing ENSIME Sublime

Rather than installing ENSIME Sublime via Package Control, check out the Git repo
directly into the directory you end up in when you choose *Preferences / Browse Packages*.

This will Sublime Text to pick up changes in the plugin codebase live as you edit it!

### Configuring ENSIME Sublime

By default, when you run the *Ensime: Startup* command, ENSIME Sublime starts a new instance of ENSIME Server.
If you are hacking on ENSIME Server, you may find it useful to disable this behaviour.

To get ENSIME to connect to a pre-existing server instead,
go to *Preferences / Package Settings / Ensime / Settings - User` and add the following config entry:

~~~ javascript
{
  // other config entries...
  "connect_to_external_server": false
}
~~~

To revert to the default behaviour, set the entry back to `true`.

## Contacts

Submit issues on the [tracker](https://github.com/ensime/ensime-sublime/issues)
or come find us on [Gitter](https://gitter.im/ensime/ensime-sublime).

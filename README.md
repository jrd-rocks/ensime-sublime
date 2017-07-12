## Introduction
This is a beta write of the new enisme plugin for sublime-text 3. The documentation for the stable ensime-sublime plugin is at http://ensime.org/editors/sublime/

## Setup
If you have been using the _Ensime_ plugin for sublime-text, first remove it through _Package Control_. This can be done by the following steps:
1. Go to _'Preferences'->'Package Control'_
2. Select _'Remove Package'_
3. Select _'Ensime'_

To then try out this beta version of ensime-sublime on sublime-text you need to:

1. Open the _Packages_ directory of sublime-text.

To go to your packages directory open sublime-text and go to _'Preferences' -> 'Browse Packages'_.
This opens up the _Packages_ directory in the explorer window.

For GNU/linux systems the _Packages_ directory for sublime text is generally at _'~/.config/sublime-text-3/Packages/'_

2. Clone the repository at https://github.com/VC1995/ensime-sublime here and checkout the _rewrite_ branch.  

**EASY WAY** (for GNU/Linux systems) : Once in the _Packages_ directory, open the directory in the terminal through _'Open in terminal'_ from context menu and run the following command : 

```
$ git clone -b rewrite https://github.com/VC1995/ensime-sublime
```

Once you have done this, you must restart sublime-text if it was open. If it worked you should now see _'Ensime'_ in the _'Tools'_ menu of sublime-text.  

You may now open up your scala project in sublime-text. This can be done through _'File' -> 'Open Folder'_ and selecting the root folder(one containing the .ensime file) of your project.

**If you haven't yet created any _.ensime_ file for your project, that's what you must do next. Instructions for doing so can be found at http://ensime.org/build_tools/sbt/**

**NOTE**
If you have been using an old version of ensime, update ensime before trying out this plugin. The version is decided through line _addSbtPlugin("org.ensime" % "sbt-ensime" % "**version**")_  in file _~/.sbt/0.13/plugins/plugins.sbt_

## Startup
The ensime server can the be started by going to _'Tools' -> 'Ensime' -> 'Maintainence' -> 'Startup'_ 
You can see the logs being generated in _'<project_directory>/.ensime-cache/'_. Once connection to ensime-server is established, errors are highlighted and shown in any of the scala files that were already open.

Opening a file in a new tab on the same window now leads to typechecing the file and highlights errors if any.
The file is also typechecked post a save operation, which redraws the highlighted areas. However modifying a file doesn't lead to any change in the highlighted areas.

The errors and warning messages are shown by default when ensime server is started. Once hidden(by clicking on any of the close icons), you can display them again by either pressing _(Ctrl+alt+e)_ or going to _'Tools'->'Ensime'->'Development'->'Show errors and warnings'_. 

### 'Go to definition'
(or jump to source) can be called either through the context menu(which appears by right clicking anywhere on the view) or through _(Ctrl+left_mouse_button)_.
The position used to pick up the symbol for _'Go to definition'_ is either the cursor target or beggining of selection if any and not where the mouse is clicked. The behavior is undefined when you have multiple cursors(a feature of sublime-text) and is set not to work if there are more than 2 cursors. 

### Refactoring
The refactoring options available are **'Add import'**, **'Organise imports'**, **'Rename'** and **'Inline local'**. The keyboard shortcuts for _'Add import'_ and _'Organise imports'_ are _'Ctrl+alt+i'_ and _'Ctrl+alt+o'_ respectively, while the other two are accessible only through the context menu.
The _'Rename'_ option requires a single selected are in the view that contains the symbol to be renamed.

## Shutdown
The server can be shutdown by going to _'Tools'->'Ensime'->'Maintenance'->'Shutdown'_. Same can be confirmed through the logs. This removes the highlights from any open view.

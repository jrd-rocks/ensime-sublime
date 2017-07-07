To try out ensime-sublime on sublime text: 

Clone the repository in the following location:
'~/.config/sublime-text-3/Packages/'
If you can't find this: Go to 'Preferences' -> 'Browse Packages' in sublime-text

Restart sublime and open up your scala project through : 'File' -> 'Open Folder'

Go to 'Tools' -> 'Ensime' -> 'Maintainence' -> 'Startup' to start up the server.
You can see the files and logs being generated in ".ensime-cache/" in the project directory.

Opening a new file and saving a file leads to typechecing the file and highlights errors if any.

'Go to definition' can be called either through the context menu(by right clicking) or Ctrl+left_mouse_button.
The position used for 'Go to definition' is either the cursor target or beggining of selection if any(not necessarily where mouse is clicked). The behavior is undefined when you have multiple cursors.

The context menu also shows 'Add Import' but it's still work in progress. It works through the context menu but is not smart yet, i.e., if your cursor is on Path and you right click and select 'Ensime'->'Development'->'Add Import', then chose java.nio.Path(say) it will be added as an import even if it was already there and not needed.

The server can be shutdown by going to 'Tools'->'Ensime'->'Maintenance'->'Shutdown'. You can confirm this through the logs.

To get more information in the log files, you may set "debug" to true in 'Ensime.sublime-settings' file in the plugin directory.

To be continued ...
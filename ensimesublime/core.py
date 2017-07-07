import sublime
import sublime_plugin

from paths import relative_path, is_subpath
import env


class EnsimeCommon(object):
    def __init__(self, owner):
        if type(owner) == sublime.Window:
            self.w = owner
            self.v = None
        elif type(owner) == sublime.View:
            # owner.window() is sometimes None
            self.w = owner.window() or sublime.active_window()
            self.v = owner
        else:
            raise Exception("unsupported owner of type: " + str(type(owner)))
        self.env = env.getOrCreateNew(self.w)

    def is_valid(self):
        return bool(self.env and self.env.valid)

    def is_running(self):
        return self.is_valid() and self.env.running


class EnsimeWindowCommand(EnsimeCommon, sublime_plugin.WindowCommand):
    def __init__(self, window):
        super(EnsimeWindowCommand, self).__init__(window)
        self.window = window


class EnsimeTextCommand(EnsimeCommon, sublime_plugin.TextCommand):
    def __init__(self, view):
        super(EnsimeTextCommand, self).__init__(view)
        self.view = view

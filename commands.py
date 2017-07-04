import sys
import sublime_plugin
import sublime

from .ensimesublime.core import EnsimeWindowCommand, EnsimeTextCommand
from .ensimesublime.env import getEnvironment
from .ensimesublime.launcher import EnsimeLauncher
from .ensimesublime.client import EnsimeClient
from .ensimesublime.outgoing import TypeCheckFilesReq


class EnsimeStartup(EnsimeWindowCommand):
    def is_enabled(self):
        # should we check self.env.valid ?
        return bool(self.env and not self.env.is_running())

    def run(self):
        try:
            self.env.recalc()
        except Exception:
            typ, value, traceback = sys.exc_info()
            self.error_message("Got an error :\n{t} : {val}\n{trace}"
                               .format(t=typ, val=str(value).split(".")[-1], trace=traceback))
        else:
            launcher = EnsimeLauncher(self.env.config)
            self.env.client = EnsimeClient(self.env, launcher)
            self.env.client.setup()


class EnsimeShutdown(EnsimeWindowCommand):
    def is_enabled(self):
        return bool(self.env and self.env.is_running())

    def run(self):
        self.env.client.teardown()


class EnsimeEventListener(sublime_plugin.EventListener):
    def on_load_async(self, view):
        env = getEnvironment(view.window())
        if env:
            if env.is_connected():
                call_id = TypeCheckFilesReq([view.file_name()]).run_in(env)
                env.client.get_response(call_id)

    def on_post_save_async(self, view):
        env = getEnvironment(view.window())
        if env:
            if env.is_connected():
                call_id = TypeCheckFilesReq([view.file_name()]).run_in(env)
                env.client.get_response(call_id)

    def on_activated_async(self, view):
        env = getEnvironment(view.window())
        if env:
            if env.is_connected():
                env.editor.colorize(view)


class PrivateToolViewAppendCommand(EnsimeTextCommand):
    def run(self, edit, content):
        selection_was_at_end = len(self.v.sel()) == 1 and self.v.sel()[0] == sublime.Region(self.v.size())
        self.view.insert(edit, self.view.size(), content)
        if selection_was_at_end:
            self.view.show(self.view.size())

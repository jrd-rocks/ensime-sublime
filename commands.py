import sys
import sublime_plugin
import sublime

from .ensimesublime.core import EnsimeWindowCommand, EnsimeTextCommand
from .ensimesublime.env import getEnvironment
from .ensimesublime.launcher import EnsimeLauncher
from .ensimesublime.client import EnsimeClient
from .ensimesublime.outgoing import TypeCheckFilesReq, SymbolAtPointReq, ImportSuggestionsReq


class EnsimeStartup(EnsimeWindowCommand):
    def is_enabled(self):
        # should we check self.env.valid ?
        return bool(self.env and not self.env.is_running())

    def run(self):
        try:
            self.env.recalc()
        except Exception:
            typ, value, traceback = sys.exc_info()
            self.error_message("Got an error :\n{t} : {val}"
                               .format(t=typ, val=str(value).split(".")[-1]))
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
                TypeCheckFilesReq([view.file_name()]).run_in(env)

    def on_post_save_async(self, view):
        env = getEnvironment(view.window())
        if env:
            if env.is_connected():
                TypeCheckFilesReq([view.file_name()]).run_in(env)

    def on_activated_async(self, view):
        env = getEnvironment(view.window())
        if env:
            if env.is_connected():
                env.editor.colorize(view)


class EnsimeGoToDefinition(EnsimeTextCommand):
    def run(self, edit, target=None):
        env = getEnvironment(self.view.window())
        if env and env.is_connected():
            pos = int(target or self.view.sel()[0].begin())
            SymbolAtPointReq(self.view.file_name(), pos).run_in(env)


class EnsimeAddImport(EnsimeTextCommand):
    def run(self, edit, target=None):
        env = getEnvironment(self.view.window())
        if env and env.is_connected():
            pos = int(target or self.view.sel()[0].begin())
            if self.view.is_dirty():
                self.view.run_command('save')
            ImportSuggestionsReq(pos,
                                 self.view.file_name(),
                                 self.view.substr(self.view.word(pos))).run_in(env)

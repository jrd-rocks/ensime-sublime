import sublime_plugin
import sublime

import sys
from functools import partial as bind

from core import EnsimeWindowCommand, EnsimeTextCommand
from env import getEnvironment
from launcher import EnsimeLauncher
from client import EnsimeClient
from outgoing import TypeCheckFilesReq, SymbolAtPointReq, ImportSuggestionsReq, OrganiseImports


class EnsimeStartup(EnsimeWindowCommand):
    def is_enabled(self):
        # should we check self.env.valid ?
        return bool(self.env and not self.env.is_running())

    def run(self):
        try:
            self.env.recalc()
        except Exception:
            typ, value, traceback = sys.exc_info()
            self.env.error_message("Got an error :\n{t} : {val}"
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


class EnsimeShowErrors(EnsimeWindowCommand):
    def is_enabled(self):
        return bool(self.env and self.env.is_connected() and len(self.env.window.views()) > 0)

    def run(self):
        self.env.editor.show_errors = True
        self.env.editor.redraw_all_highlights()


class EnsimeEventListener(sublime_plugin.EventListener):
    def on_load(self, view):
        env = getEnvironment(view.window())
        if env:
            if env.is_connected():
                TypeCheckFilesReq([view.file_name()]).run_in(env, async=True)

    def on_post_save(self, view):
        env = getEnvironment(view.window())
        if env:
            if env.is_connected():
                TypeCheckFilesReq([view.file_name()]).run_in(env, async=True)


class EnsimeGoToDefinition(EnsimeTextCommand):
    def run(self, edit, target=None):
        env = getEnvironment(self.view.window())
        if env and env.is_connected():
            if len(self.view.sel()) > 2:
                env.status_message("You have multiple cursors. Trying to confuse ensime, eh?")
                return
            pos = int(target or self.view.sel()[0].begin())
            SymbolAtPointReq(self.view.file_name(), pos).run_in(env, async=True)


class EnsimeAddImport(EnsimeTextCommand):
    def run(self, edit, target=None):
        env = getEnvironment(self.view.window())
        if env and env.is_connected():
            pos = int(target or self.view.sel()[0].begin())
            if self.view.is_dirty():
                self.view.run_command('save')
            ImportSuggestionsReq(pos,
                                 self.view.file_name(),
                                 self.view.substr(self.view.word(pos))).run_in(env, async=True)


class EnsimeOrganiseImports(EnsimeTextCommand):
    def run(self, edit):
        env = getEnvironment(self.view.window())
        if env and env.is_connected():
            if self.view.is_dirty():
                self.view.run_command('save')
            OrganiseImports(self.view.file_name()).run_in(env, async=True)

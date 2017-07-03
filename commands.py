import sys
import sublime_plugin

from .ensimesublime.core import EnsimeWindowCommand, EnsimeCommon
from .ensimesublime.launcher import EnsimeLauncher
from .ensimesublime.client import EnsimeClient
from .ensimesublime.outgoing import TypeCheckFileReq


class EnsimeStartup(EnsimeWindowCommand):
    def is_enabled(self):
        # should we check self.env.valid ?
        return bool(self.env and not self.env.running)

    def run(self):
        try:
            self.env.recalc()
        except Exception:
            typ, value, traceback = sys.exc_info()
            self.error_message("Got an error :\n{t} : {val}"
                               .format(t=typ, val=str(value).split(".")[-1]))
        else:
            l = EnsimeLauncher(self.env.config)
            self.env.client = EnsimeClient(self.env.logger, l, self.env.connection_timeout)
            self.env.client.setup()


class EnsimeShutdown(EnsimeWindowCommand):
    def is_enabled(self):
        return bool(self.env and self.env.running)

    def run(self):
        self.env.client.teardown()


class EnsimeEventListener(EnsimeCommon, sublime_plugin.EventListener):
    def on_load(self, view):
        if self.is_running() and self.in_project():
            TypeCheckFileReq(view.file_name()).run(self.env.client)

    def on_post_save(self, view):
        pass

    def on_activated(self, view):
        pass
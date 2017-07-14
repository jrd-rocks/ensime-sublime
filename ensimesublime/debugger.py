# coding: utf-8
import sublime

import json
import os
import tempfile
from functools import partial as bind

from config import feedback


class DebugHandler(object):
    """This is the implementation of the Ensime debug handler, it must be mixed in
       with the EnsimeClient to be useful."""

    def handle_debug_output(self, call_id, payload):
        """Handle responses `DebugOutputEvent`."""
        sublime.set_timeout(bind(sublime.message_dialog,
                                 payload["body"].encode("ascii", "ignore")), 0)

    def handle_debug_break(self, call_id, payload):
        """Handle responses `DebugBreakEvent`."""
        line = payload['line']
        path = os.path.relpath(payload['file'], self.env.project_root)

        sublime.set_timeout(bind(sublime.message_dialog,
                                 feedback['notify_break'].format(line, path)), 0)
        self.debug_thread_id = payload["threadId"]

    # TODO: This leaves a lot to be desired...
    def handle_debug_backtrace(self, call_id, payload):
        """Handle responses `DebugBacktrace`."""
        frames = payload["frames"]
        fd, path = tempfile.mkstemp('.json', text=True, dir=self.tmp_diff_folder)
        tmpfile = os.fdopen(fd, 'w')

        tmpfile.write(json.dumps(frames, indent=2))
        opts = {'readonly': True, 'bufhidden': 'wipe',
                'buflisted': False, 'swapfile': False}
        self.editor.split_window(path, size=20, bufopts=opts)
        tmpfile.close()

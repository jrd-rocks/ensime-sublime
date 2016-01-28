from __future__ import unicode_literals
import sublime
from sublime import *
from sublime_plugin import *
import threading
import _thread
import socket
import getpass
import errno
import subprocess
import time
import traceback
import random
import uuid
from functools import partial as bind
from os import path
from .paths import *
from types import *
import collections
import re
import html
import webbrowser

from .server import *
from . import env, dotensime, dotsession, rpc, sexp
from .sexp import key, sym
from .constants import *
from .rpc import *
from .sbt import *
from .strings import *


class EnsimeCommon(object):
    def __init__(self, owner):
        self.owner = owner
        if type(owner) == Window:
            self._env = env.for_window(owner)
            if self._env:
                self.logger = self._env.logger
                self._recalc_session_id()
            self.w = owner
        elif type(owner) == View:
            # todo. find out why owner.window() is sometimes None
            w = owner.window() or sublime.active_window()
            self._env = env.for_window(w)
            if self._env:
                self.logger = self._env.logger
                self._recalc_session_id()
            self.w = w
            self.v = owner
        else:
            raise Exception("unsupported owner of type: " + str(type(owner)))

    def is_enabled(self):
        return self.is_valid()

    @property
    def env(self):
        if not self._env:
            self._env = env.for_window(self.w)
            self._recalc_session_id()
        return self._env

    def _recalc_session_id(self):
        self.session_id = self._env.session_id if self._env else None

    @property
    def rpc(self):
        return self.env.rpc

    def status_message(self, msg):
        sublime.set_timeout(bind(sublime.status_message, msg), 0)

    def error_message(self, msg):
        sublime.set_timeout(bind(sublime.error_message, msg), 0)

    def is_valid(self):
        return bool(self.env and self.env.valid)

    def is_running(self):
        return self.is_valid() and self.env.running

    def _filename_from_wannabe(self, wannabe):
        if type(wannabe) == type(None):
            v = self.v if hasattr(self, "v") else self.w.active_view()
            return self._filename_from_wannabe(v) if v is not None else None
        if type(wannabe) == sublime.View:
            return wannabe.file_name()
        return wannabe

    def in_project(self, wannabe=None):
        filename = self._filename_from_wannabe(wannabe)
        extension_ok = bool(filename and (filename.endswith("scala") or filename.endswith("java")))
        subpath_ok = bool(self.env and is_subpath(self.env.project_root, filename))
        return extension_ok and subpath_ok

    def project_relative_path(self, wannabe):
        filename = self._filename_from_wannabe(wannabe)
        if not self.in_project(filename):
            return None
        return relative_path(self.env.project_root, filename)

    def _invoke_view_colorer(self, method, *args):
        view = args[0]
        args = args[1:]
        if view == "default":
            view = self.v
        if view is not None:
            colorer = Colorer(view)
            getattr(colorer, method)(*args)

    def _invoke_all_colorers(self, method, *args):
        for i in range(0, self.w.num_groups()):
            if self.w.views_in_group(i):
                v = self.w.active_view_in_group(i)
                colorer = Colorer(v)
                getattr(colorer, method)(*args)

    def colorize(self, view="default"):
        self._invoke_view_colorer("colorize", view)

    def colorize_all(self):
        self._invoke_all_colorers("colorize")

    def uncolorize(self, view="default"):
        self._invoke_view_colorer("uncolorize", view)

    def uncolorize_all(self):
        self._invoke_all_colorers("uncolorize")

    def redraw_highlights(self, view="default"):
        self._invoke_view_colorer("redraw_highlights", view)

    def redraw_all_highlights(self):
        self._invoke_all_colorers("redraw_highlights")

    def redraw_status(self, view="default"):
        self._invoke_view_colorer("redraw_status", view)

    def redraw_breakpoints(self, view="default"):
        self._invoke_view_colorer("redraw_breakpoints", view)

    def redraw_all_breakpoints(self):
        self._invoke_all_colorers("redraw_breakpoints")

    def redraw_debug_focus(self, view="default"):
        self._invoke_view_colorer("redraw_debug_focus", view)

    def redraw_all_debug_focuses(self):
        self._invoke_all_colorers("redraw_debug_focus")

    def redraw_stack_focus(self, view="default"):
        self._invoke_view_colorer("redraw_stack_focus", view)

    def redraw_all_stack_focuses(self):
        self._invoke_all_colorers("redraw_stack_focus")


class EnsimeWindowCommand(EnsimeCommon, WindowCommand):
    def __init__(self, window):
        super(EnsimeWindowCommand, self).__init__(window)
        self.window = window


class EnsimeTextCommand(EnsimeCommon, TextCommand):
    def __init__(self, view):
        super(EnsimeTextCommand, self).__init__(view)
        self.view = view


class EnsimeEventListener(EnsimeCommon):
    pass


class EnsimeEventListenerProxy(EventListener):
    def __init__(self):
        def is_ensime_event_listener(member):
            return inspect.isclass(member) and member != EnsimeEventListener and issubclass(member, EnsimeEventListener)

        self.listeners = [info[1] for info in inspect.getmembers(sys.modules[__name__], is_ensime_event_listener)]

    def _invoke(self, view, handler_name, *args):
        for listener in self.listeners:
            instance = listener(view)
            try:
                handler = getattr(instance, handler_name)
            except:
                handler = None
            if handler:
                return handler(*args)

    def on_new(self, view):
        return self._invoke(view, "on_new")

    def on_clone(self, view):
        return self._invoke(view, "on_clone")

    def on_load(self, view):
        return self._invoke(view, "on_load")

    def on_close(self, view):
        return self._invoke(view, "on_close")

    def on_pre_save(self, view):
        return self._invoke(view, "on_pre_save")

    def on_post_save(self, view):
        return self._invoke(view, "on_post_save")

    def on_modified(self, view):
        return self._invoke(view, "on_modified")

    def on_selection_modified(self, view):
        return self._invoke(view, "on_selection_modified")

    def on_activated(self, view):
        return self._invoke(view, "on_activated")

    def on_deactivated(self, view):
        return self._invoke(view, "on_deactivated")

    def on_query_context(self, view, key, operator, operand, match_all):
        return self._invoke(view, "on_query_context", key, operator, operand, match_all)

    def on_query_completions(self, view, prefix, locations):
        return self._invoke(view, "on_query_completions", prefix, locations)


class ValidOnly:
    def is_enabled(self):
        return self.is_valid()


class ProjectDoesntExist:
    def is_enabled(self):
        return not dotensime.exists(self.w)


class ProjectExists:
    def is_enabled(self):
        return dotensime.exists(self.w)


class NotRunningOnly:
    def is_enabled(self):
        return not self.is_running()


class RunningOnly:
    def is_enabled(self):
        return self.is_running()


class RunningProjectFileOnly:
    def is_enabled(self):
        return self.is_running() and self.in_project()


class ProjectFileOnly:
    def is_enabled(self):
        return self.in_project()


class NotDebuggingOnly:
    def is_enabled(self):
        return bool(self.is_running() and not self.env.profile)


class DebuggingOnly:
    def is_enabled(self):
        return bool(self.is_running() and self.env.profile)


class FocusedOnly:
    def is_enabled(self):
        return bool(self.is_running() and self.env.focus)


class PrivateToolViewUpdateCommand(EnsimeTextCommand):
    def run(self, edit, content):
        self.view.replace(edit, Region(0, self.view.size()), content)
        self.view.sel().clear()
        self.view.sel().add(Region(0, 0))


class PrivateToolViewAppendCommand(EnsimeTextCommand):
    def run(self, edit, content):
        selection_was_at_end = len(self.v.sel()) == 1 and self.v.sel()[0] == sublime.Region(self.v.size())
        self.view.insert(edit, self.view.size(), content)
        if selection_was_at_end:
            self.view.show(self.view.size())


class EnsimeToolView(EnsimeCommon):
    def __init__(self, env):
        super(EnsimeToolView, self).__init__(env.w)

    def can_show(self):
        raise Exception("abstract method: EnsimeToolView.can_show(self)")

    @property
    def name(self):
        raise Exception("abstract method: EnsimeToolView.name(self)")

    def render(self):
        raise Exception("abstract method: EnsimeToolView.render(self)")

    def setup_events(self, v):
        v.settings().set("result_file_regex", "([:.a-z_A-Z0-9\\\\/-]+[.](?:scala|java)):([0-9]+)")
        v.settings().set("result_line_regex", "")
        v.settings().set("result_base_dir", self.env.project_root)
        other_view = self.w.new_file()
        self.w.focus_view(other_view)
        self.w.run_command("close_file")
        self.w.focus_view(v)

    def handle_event(self, event, target):
        pass

    @property
    def v(self):
        wannabes = [v for v in self.w.views() if v.name() == self.name]
        return next(iter(wannabes), None)

    def _mk_v(self):
        v = self.w.new_file()
        v.set_scratch(True)
        v.set_name(self.name)
        self.setup_events(v)
        return v

    def _update_v(self, content):
        if self.v is not None:
            self.v.run_command("private_tool_view_update", {'content': content})

    def clear(self):
        self._update_v("")

    # TODO: ideally, rendering should only happen when a tool view is visible
    def refresh(self):
        if self.v is not None:
            content = self.render() or ""
            self._update_v(content)

    def show(self):
        if self.v is None:
            self._mk_v()
            self.refresh()
        self.w.focus_view(self.v)


# ############################# LOW-LEVEL: CLIENT & SERVER ##############################

class ClientListener:
    def on_client_async_data(self, data):
        pass


class ClientSocket(EnsimeCommon):
    def __init__(self, owner, port, timeout, handlers):
        super(ClientSocket, self).__init__(owner)
        self.port = port
        self.timeout = timeout
        self.connected = False
        self.handlers = handlers
        self._lock = threading.RLock()
        self._connect_lock = threading.RLock()
        self._receiver = None
        self.socket = None

    def notify_async_data(self, data):
        for handler in self.handlers:
            if handler:
                handler.on_client_async_data(data)

    def receive_loop(self):
        while self.is_connected():
            try:
                msglen = self.socket.recv(6)
                if msglen:
                    msglen = int(msglen, 16)

                    buf = self.socket.recv(msglen)
                    while len(buf) < msglen:
                        chunk = self.socket.recv(msglen - len(buf))
                        if chunk:
                            buf += chunk
                        else:
                            raise Exception("fatal error: recv returned None")

                    try:
                        s = buf.decode('utf-8')
                        form = sexp.read(s)
                        self.notify_async_data(form)
                    except:
                        self.logger.warn("failed to parse incoming message")
                        raise
                else:
                    raise Exception("fatal error: recv returned None")
            except Exception:
                if self.is_connected():
                    self.logger.error("*****    ERROR     *****")
                    self.logger.error(traceback.format_exc())
                    self.connected = False
                    self.status_message("Ensime server has disconnected")
                    # todo. do we need to check session_ids somewhere else as well?
                    if self.env.session_id == self.session_id:
                        self.env.controller.shutdown()
                    else:
                        self.logger.warn("Client Socket closed")

    def start_receiving(self):
        t = threading.Thread(name="ensime-client-" + str(self.w.id()) + "-" + str(self.port), target=self.receive_loop)
        t.setDaemon(True)
        t.start()
        self._receiver = t

    def connect(self):
        self._connect_lock.acquire()
        host = "127.0.0.1"
        try:
            s = socket.socket()
            s.settimeout(self.timeout)
            s.connect((host, self.port))
            s.settimeout(None)
            self.socket = s
            self.connected = True
            self.start_receiving()
            self.status_message("Successfully connected to Ensime server at " + host + ":" + str(self.port))
            return s
        except socket.error as e:
            self.connected = False
            self.logger.error("Cannot connect to Ensime server:  " + str(e.args))
            self.status_message("Cannot connect to Ensime server at " + host + ":" + str(self.port) + " " + str(e.args))
            self.env.controller.shutdown()
        finally:
            self._connect_lock.release()

    def is_connected(self):
        self._connect_lock.acquire()
        try:
            return self.connected
        finally:
            self._connect_lock.release()

    def send(self, request):
        try:
            if not self.connected:
                self.connect()
            self.socket.send(request)
        except:
            self.connected = False

    def close(self):
        self._connect_lock.acquire()
        try:
            if self.socket:
                self.socket.close()
        finally:
            self.connected = False
            self._connect_lock.release()


class Client(ClientListener, EnsimeCommon):
    def __init__(self, owner, port_file, http_port_file, timeout):
        super(Client, self).__init__(owner)
        with open(port_file) as f:
            self.port = int(f.read())
        with open(http_port_file) as f:
            self.http_port = int(f.read())
        self.timeout = timeout
        self.init_counters()
        methods = [m for m in inspect.getmembers(self, predicate=inspect.ismethod) if m[0].startswith("message_")]
        self.logger.debug("reflectively found " + str(len(methods)) + " message handlers: " + str(methods))
        self.handlers = dict((":" + m[0][len("message_"):].replace("_", "-"), (m[1], None, None)) for m in methods)
        self.socket = None

    def startup(self):
        self.logger.info("Starting Ensime client (plugin version is " +
                         (self.env.settings.get("plugin_version") or "unknown") + ")")
        self.logger.info("Launching Ensime client socket at port " + str(self.port))
        self.status_message("Starting Ensime...")
        self.socket = ClientSocket(self.owner, self.port, self.timeout, [self, self.env.controller])
        s = self.socket.connect()
        self.logger.info("Requesting connection info")
        self.rpc.connection_info()
        return s

    def shutdown(self):
        print("shutdown() called")
        if self.socket.connected:
            self.rpc.shutdown_server()
        self.socket.close()
        self.socket = None

    def async_req(self, to_send, on_complete=None, call_back_into_ui_thread=None):
        if on_complete is not None and call_back_into_ui_thread is None:
            raise Exception("must specify a threading policy when providing a non-empty callback")
        if not self.socket:
            raise Exception("socket is either not yet initialized or is already destroyed")

        msg_id = self.next_message_id()
        self.handlers[msg_id] = (on_complete, call_back_into_ui_thread, time.time())
        msg = sexp.to_string([key(":swank-rpc"), to_send, msg_id])
        encoded_msg = msg.encode('utf-8')
        self.logger.info("request #" + str(msg_id) + "(async) send - " + str(encoded_msg[0:100]) + "...")
        msg_bytes = ("%06x" % len(encoded_msg)).encode('utf-8') + encoded_msg
        self.logger.debug("async_req: " + str(msg_id) + "  " + str(msg_bytes))
        self.socket.send(msg_bytes)

    def sync_req(self, to_send, timeout=0):
        msg_id = self.next_message_id()
        event = threading.Event()
        self.handlers[msg_id] = (event, None, time.time())
        msg = sexp.to_string([key(":swank-rpc"), to_send, msg_id])
        encoded_msg = msg.encode('utf-8')
        msg_bytes = ("%06x" % len(encoded_msg)).encode('utf-8') + encoded_msg
        self.logger.info("request #" + str(msg_id) + "(sync) send - " + str(encoded_msg[0:100]) + "...")
        self.logger.debug("sync_req: " + str(msg_bytes))
        self.socket.send(msg_bytes)

        max_wait = timeout or self.timeout
        event.wait(max_wait)
        if hasattr(event, "payload"):
            return event.payload
        else:
            self.logger.warn("sync_req #" + str(msg_id) + " has timed out (didn't get a response after " +
                             str(max_wait) + " seconds)")
            return None

    def on_client_async_data(self, data):
        self.logger.debug("on_client_async_data: " + str(data))
        self.handle_message(data)

    def handle_message(self, data):
        msg_type = str(data[0])
        handler = self.handlers.get(msg_type)
        if handler:
            handler, _, _ = handler
            msg_id = data[-1] if msg_type == ":return" else None
            data = data[1:-1] if msg_type == ":return" else data[1:]
            payload = None
            if len(data) == 1:
                payload = data[0]
            if len(data) > 1:
                payload = data
            return handler(msg_id, payload)
        else:
            self.logger.warn("handle_message: unexpected message type: " + msg_type)

    def message_return(self, msg_id, payload):
        handler, call_back_into_ui_thread, req_time = self.handlers.get(msg_id)
        if handler:
            del self.handlers[msg_id]

        def invoke_subscribed_handler(success, payload=None):
            if isinstance(handler, collections.Callable):
                # only do async callbacks if the result is a success
                # however note that we need to ping sync callbacks in any case
                # in order to prevent freezes upon erroneous responses
                if call_back_into_ui_thread and success:
                    sublime.set_timeout(bind(handler, payload), 0)
                else:
                    handler(payload)
            else:
                handler.payload = payload
                handler.set()

        resp_time = time.time()
        self.logger.info("request #" + str(msg_id) + " took " + str(resp_time - req_time) + " seconds")

        reply_type = str(payload[0])
        if reply_type == ":ok":
            payload = payload[1]
            if handler:
                invoke_subscribed_handler(success=True, payload=payload)
            else:
                self.logger.warn("warning: no handler registered for message #" + str(msg_id) +
                                 " with payload " + str(payload))
        # (:return (:abort 210 "Error occurred in Analyzer. Check the server log.") 3)
        elif reply_type == ":abort":
            detail = payload[2]
            if msg_id <= 1:  # initialize project
                self.error_message(self.prettify_error_detail(detail))
                self.status_message("Ensime startup has failed")
                self.env.controller.shutdown()
            else:
                invoke_subscribed_handler(success=False)
                self.status_message(detail)
        # (:return (:error NNN "SSS") 4)
        elif reply_type == ":error":
            detail = payload[2]
            invoke_subscribed_handler(success=False)
            self.error_message(self.prettify_error_detail(detail))
        else:
            invoke_subscribed_handler(success=False)
            self.logger.warn("unexpected reply type: " + reply_type)

    def call_back_into_ui_thread(vanilla):
        def wrapped(self, msg_id, payload):
            sublime.set_timeout(bind(vanilla, self, msg_id, payload), 0)

        return wrapped

    @call_back_into_ui_thread
    def message_compiler_ready(self, msg_id, payload):
        self.env.compiler_ready = True
        quotes = ["Let the hacking commence!",
                  "Hacks and glory await!",
                  "Hack and be merry!",
                  "May the source be with you!",
                  "Death to null!",
                  "Find closure!",
                  "May the _ be with you.",
                  "CanBuildFrom[List[Dream], Reality, List[Reality]]"]
        msg = quotes[random.randint(0, len(quotes) - 1)]
        self.status_message(
            msg + " This could be the start of a beautiful program, " + getpass.getuser().capitalize() + ".")
        self.colorize_all()
        v = self.w.active_view()
        if self.in_project(v):
            v.run_command("save")

    @call_back_into_ui_thread
    def message_compiler_restarted(self, msg_id, payload):
        pass

    @call_back_into_ui_thread
    def message_indexer_ready(self, msg_id, payload):
        pass

    @call_back_into_ui_thread
    def message_full_typecheck_finished(self, msg_id, payload):
        pass

    @call_back_into_ui_thread
    def message_background_message(self, msg_id, payload):
        # (:background-message 105 "Initializing Analyzer. Please wait...")
        self.status_message(payload[1])

    def _update_note_ui(self):
        self.redraw_all_highlights()
        v = self.w.active_view()
        if v is not None:
            self.env.notee = v
            self.env.notes.refresh()

    @call_back_into_ui_thread
    def message_java_notes(self, msg_id, payload):
        self.env.notes_storage.append(rpc.Note.parse_list(payload))
        self._update_note_ui()

    @call_back_into_ui_thread
    def message_scala_notes(self, msg_id, payload):
        self.env.notes_storage.append(rpc.Note.parse_list(payload))
        self._update_note_ui()

    @call_back_into_ui_thread
    def message_clear_all_java_notes(self, msg_id, _):
        self.env.notes_storage.filter(lambda n: not n.file_name.endswith(".java"))
        self._update_note_ui()

    @call_back_into_ui_thread
    def message_clear_all_scala_notes(self, msg_id, _):
        self.env.notes_storage.filter(lambda n: not n.file_name.endswith(".scala"))
        self._update_note_ui()

    @call_back_into_ui_thread
    def message_debug_event(self, msg_id, payload):
        debug_event = rpc.DebugEvent.parse(payload)
        if debug_event:
            self.env.debugger.handle(debug_event)

    def init_counters(self):
        self._counter = 0
        self._counterLock = threading.RLock()

    def next_message_id(self):
        self._counterLock.acquire()
        try:
            self._counter += 1
            return self._counter
        finally:
            self._counterLock.release()

    def prettify_error_detail(self, detail):
        detail = "Ensime server has encountered a fatal error: " + detail
        if detail.endswith(". Check the server log."):
            detail = detail[0:-len(". Check the server log.")]
        if not detail.endswith("."):
            detail += "."
        detail += "\n\nCheck the server log at " + str(self.env.log_file) + "."
        return detail

    def open_uri(self, uri):
        url = "http://localhost:" + str(self.http_port) + "/" + uri
        webbrowser.open_new_tab(url)


class ServerListener:
    def on_server_data(self, data):
        pass


class ServerProcess(EnsimeCommon):
    def __init__(self, owner, command, run_dir, listeners):
        super(ServerProcess, self).__init__(owner)
        self.logger.info("Starting: " + str(command))
        self.logger.info("Run dir: " + run_dir)
        self.killed = False
        self.listeners = listeners or []

        exec_env = os.environ.copy()
        # if not "-Densime.explode.on.disconnect" in args:
        #     args += " -Densime.explode.on.disconnect=1"
        # env["ENSIME_JVM_ARGS"] = str(args)  # unicode not supported here

        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow |= 1  # SW_SHOWNORMAL
            creationflags = 0x8000000  # CREATE_NO_WINDOW
            self.proc = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startupinfo=startupinfo,
                creationflags=creationflags,
                env=exec_env,
                cwd=run_dir)
        else:
            self.proc = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=exec_env,
                cwd=run_dir)
        self.logger.info("started ensime server with pid " + str(self.proc.pid))

        if self.proc.stdout:
            _thread.start_new_thread(self.read_stdout, ())

        if self.proc.stderr:
            _thread.start_new_thread(self.read_stderr, ())

    def kill(self):
        if not self.killed:
            self.killed = True
            # send terminate rather than kill, so the server process cleans up nicely.
            self.proc.terminate()
            self.listeners = []

    def poll(self):
        return self.proc.poll() is None

    def read_stdout(self):
        while True:
            data = os.read(self.proc.stdout.fileno(), 2 ** 15)
            if data != b"":
                for listener in self.listeners:
                    if listener:
                        listener.on_server_data("OUT: " + str(data))
            else:
                self.proc.stdout.close()
                break

    def read_stderr(self):
        while True:
            data = os.read(self.proc.stderr.fileno(), 2 ** 15)
            if data != b"":
                for listener in self.listeners:
                    if listener:
                        listener.on_server_data("ERR: " + str(data))
            else:
                self.proc.stderr.close()
                break


class Server(ServerListener, EnsimeCommon):
    def __init__(self, owner, port_file):
        """
        :param owner: The parent window
        :param config_map: The .ensime config file as a key-value map
        :param port_file:
        :return:
        """
        super(Server, self).__init__(owner)
        self.dotensime_file = self.env.dotensime_file
        self.config_map = self.env.config_map
        self.cache_dir = self.config_map.get(":cache-dir")
        self.scala_version = self.config_map.get(":scala-version")
        self.java_home = self.config_map.get(":java-home")
        self.java_flags = self.config_map.get(":java-flags")
        self.ensime_version = "0.9.10-SNAPSHOT"
        self.port_file = port_file
        self.proc = None
        self.classpath = None

    def startup(self):
        os_sep = str(os.sep)
        self.logger.info("-----------------------------------------------------------")
        self.logger.info("Initialising server")
        self.logger.info("Cache dir = " + self.cache_dir)
        self.logger.info("Java home = " + self.java_home)
        self.logger.info("Target scala version  = " + self.scala_version)

        mkdir_p(self.cache_dir)

        resolution_dir = self.cache_dir + os_sep + "Resolution"
        mkdir_p(resolution_dir)
        classpath_file = resolution_dir + os_sep + "classpath"
        classpath_log = resolution_dir + os_sep + "saveClasspath.log"
        project_dir = resolution_dir + os_sep + "project"
        mkdir_p(project_dir)
        build_file = resolution_dir + os_sep + "build.sbt"
        build_props_file = resolution_dir + os_sep + "project" + os_sep + "build.properties"

        write_classpath_sbt_script(build_file, self.scala_version, self.ensime_version, classpath_file)
        write_build_props_file(build_props_file)

        self.logger.info("Resolving, log available in " + classpath_log)
        self.logger.info("Running sbt saveClasspath (in " + str(resolution_dir) + ")")
        self.status_message("Running sbt saveClasspath (in" + str(resolution_dir) + ")")

        cmd = sbt_binary_and_flags()

        if cmd:
            fn = bind(self.startup2)
            exec_save_classpath(self.logger, cmd, resolution_dir, classpath_file, classpath_log, fn)
        else:
            sublime.error_message("Could not find sbt. Please add sbt to your Sublime Text PATH.")

    def startup2(self, classpath):
        """
        This function will be called by a background thread - bounce to the gui thread
        :param classpath: The classpath returned from the exec_save_classpath None if resolution failed
        """
        if classpath is not None:
            sublime.set_timeout(bind(self.startup3, classpath), 0)
        else:
            # This should probably be a popup
            self.logger.info("Failed to start")

    def startup3(self, classpath):
        os_sep = str(os.sep)
        os_path_sep = str(os.pathsep)

        if classpath is not None:
            self.classpath = str(os.path.join(self.java_home, "lib","tools.jar")) + os_path_sep + classpath
            self.logger.info("Target classpath  = " + self.classpath)
        else:
            self.logger.error("Failed to generate classpath")

        self.status_message("Classpath saved, starting ensime server")
        ensime_command = self.get_ensime_command()
        if ensime_command:
            self.logger.info("Starting Ensime server (plugin version is " + (
                self.env.settings.get("plugin_version") or "unknown") + ")")
            self.logger.info(
                "Launching Ensime server process with command = " + str(ensime_command) + " and flags = " +
                str(self.java_flags))

            ensime_cfg_flag = "-Densime.config=" + self.dotensime_file
            classpath_part = ["-classpath", self.classpath, ensime_cfg_flag]
            cmd = [ensime_command] + classpath_part + self.java_flags + ["-Densime.explode.on.disconnect=true",
                                                                         "org.ensime.server.Server"]

            self.proc = ServerProcess(self.owner, cmd, self.cache_dir, [self, self.env.controller])
            return True

    def get_ensime_command(self):
        cmd = path.join(self.java_home, "bin", "java")
        return cmd

    def on_server_data(self, data):
        str_data = str(data).replace("\r\n", "\n").replace("\r", "\n")
        self.logger.info("Server: " + str_data.strip())

    def shutdown(self):
        self.proc.kill()
        self.proc = None


def mkdir_p(dir_path):
    try:
        os.makedirs(dir_path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(dir_path):
            pass
        else:
            raise


class Controller(EnsimeCommon, ClientListener, ServerListener):
    def __init__(self, env2):
        super(Controller, self).__init__(env2.w)
        self.client = None
        self.server = None
        self.port_file = None
        self.http_port_file = None

    def startup(self):
        cache_dir = self.env.cache_dir
        port_file = path.join(cache_dir, "port")
        http_port_file = path.join(cache_dir, "http")
        try:
            if not self.env.running:
                if self.env.settings.get("connect_to_external_server", False):
                    self.port_file = port_file
                    self.http_port_file = http_port_file
                    if not self.port_file:
                        message = "\"connect_to_external_server\" in your Ensime.sublime-settings is set to true, "
                        message += "however \"external_server_port_file\" is not specified. "
                        message += "Set it to a meaningful value and restart Ensime."
                        self.logger.error(message)
                        sublime.set_timeout(bind(sublime.error_message, message), 0)
                        return
                    if not os.path.exists(self.port_file):
                        message = "\"connect_to_external_server\" in your Ensime.sublime-settings is set to true, "
                        message += "however \"external_server_port_file\" is set to a non-existent file \""
                        message += (self.port_file + "\" . ")
                        message += "Check the configuration and restart Ensime."
                        self.logger.error(message)
                        sublime.set_timeout(bind(sublime.error_message, message), 0)
                        return
                    self.server = None
                    self.env.running = True
                    sublime.set_timeout(self.ignition, 0)
                else:
                    self.port_file = port_file
                    self.http_port_file = http_port_file
                    self.server = Server(self.owner, port_file)
                    self.server.startup()  # delay handshake until the port number has been written
        except:
            self.env.running = False
            raise

    def on_server_data(self, data):
        if not self.env.running and re.search("creating portfile.*http", data):
            self.logger.info("SEEN port write")
            self.env.running = True
            sublime.set_timeout(self.ignition, 0)

    def ignition(self):
        timeout = self.env.settings.get("timeout_sync_roundtrip", 3)
        self.client = Client(self.owner, self.port_file, self.http_port_file, timeout)
        self.status_message("Initializing Ensime server... ")
        self.client.startup()

    def shutdown(self):
        print("Controller shutdown() called")
        try:
            if self.env.running:
                try:
                    self.env.debugger.shutdown()
                except:
                    self.logger.error("Error shutting down ensime debugger:")
                    self.logger.error(traceback.format_exc())
                try:
                    self.env.notes_storage.clear()
                    sublime.set_timeout(self.uncolorize_all, 0)
                    sublime.set_timeout(self.env.notes.clear, 0)
                except:
                    self.logger.error("Error shutting down ensime UI:")
                    self.logger.error(traceback.format_exc())
                try:
                    if self.client:
                        self.client.shutdown()
                except:
                    self.logger.error("Error shutting down ensime client:")
                    self.logger.error(traceback.format_exc())
                try:
                    if self.server:
                        self.server.shutdown()
                except:
                    self.logger.error("Error shutting down ensime server:")
                    self.logger.error(traceback.format_exc())
        finally:
            self.port_file = None
            self.env.running = False
            self.env.compiler_ready = False
            self.client = None
            self.server = None


# ############################# ENSIME <-> SUBLIME ADAPTER ##############################

class Daemon(EnsimeEventListener):
    def on_load(self):
        if self.is_running() and self.in_project():
            self.rpc.typecheck_file(SourceFileInfo(self.v.file_name()))

    def on_post_save(self):
        if self.is_running() and self.in_project():
            self.rpc.typecheck_file(SourceFileInfo(self.v.file_name()))
        if self.env and same_paths(self.v.file_name(), self.env.session_file):
            self.env.load_session()
            self.redraw_all_breakpoints()

    def on_activated(self):
        self.colorize()
        if self.in_project():
            self.env.notee = self.v
            self.env.notes.refresh()

    def on_selection_modified(self):
        self.redraw_status()

    def on_modified(self):
        rs = self.v.get_regions(ENSIME_BREAKPOINT_REGION)
        if rs:
            irrelevant_breakpoints = [b for b in self.env.breakpoints if not same_paths(b.file_name, self.v.file_name())]

            def new_breakpoint_position(r):
                lines = self.v.lines(r)
                if lines:
                    (linum, _) = self.v.rowcol(lines[0].begin())
                    return dotsession.Breakpoint(self.v.file_name(), linum + 1)

            relevant_breakpoints = [b for b in map(new_breakpoint_position, rs) if b]
            self.env.breakpoints = irrelevant_breakpoints + relevant_breakpoints
            self.env.save_session()
            self.redraw_breakpoints()


class Colorer(EnsimeCommon):
    def colorize(self, view="default"):
        self.uncolorize()
        self.redraw_highlights()
        self.redraw_status()
        self.redraw_breakpoints()
        self.redraw_debug_focus()
        self.redraw_stack_focus()

    def uncolorize(self, view="default"):
        self.v.erase_regions(ENSIME_ERROR_OUTLINE_REGION)
        self.v.erase_regions(ENSIME_ERROR_UNDERLINE_REGION)
        # don't erase breakpoints, they should be permanent regardless of whether ensime is running or not
        # self.v.erase_regions(ENSIME_BREAKPOINT_REGION)
        self.v.erase_regions(ENSIME_DEBUGFOCUS_REGION)
        self.v.erase_regions(ENSIME_STACKFOCUS_REGION)
        self.redraw_status()

    def redraw_highlights(self, view="default"):
        self.v.erase_regions(ENSIME_ERROR_OUTLINE_REGION)
        self.v.erase_regions(ENSIME_ERROR_UNDERLINE_REGION)

        if self.env:
            relevant_notes = self.env.notes_storage.for_file(self.v.file_name())

            # Underline specific error range
            underlines = [sublime.Region(note.start, note.end) for note in relevant_notes]
            if self.env.settings.get("error_highlight") and self.env.settings.get("error_underline"):
                self.v.add_regions(
                    ENSIME_ERROR_UNDERLINE_REGION,
                    underlines + self.v.get_regions(ENSIME_ERROR_UNDERLINE_REGION),
                    self.env.settings.get("error_scope"),
                    sublime.DRAW_EMPTY_AS_OVERWRITE)

            # Outline entire errored line
            errors = [self.v.full_line(note.start) for note in relevant_notes]
            if self.env.settings.get("error_highlight"):
                self.v.add_regions(
                    ENSIME_ERROR_OUTLINE_REGION,
                    errors + self.v.get_regions(ENSIME_ERROR_OUTLINE_REGION),
                    self.env.settings.get("error_scope"),
                    self.env.settings.get("error_icon"),
                    sublime.DRAW_OUTLINED)

            # we might need to add/remove/refresh the error message in the status bar
            self.redraw_status()

            # breakpoints and debug focus should always have priority over red squiggles
            self.redraw_breakpoints()
            self.redraw_debug_focus()
            self.redraw_stack_focus()

    def redraw_status(self, custom_status=None):
        if custom_status:
            self._update_statusbar(custom_status)
        elif self.env and self.env.settings.get("ensime_statusbar_showerrors"):
            if self.v.sel():
                relevant_notes = self.env.notes_storage.for_file(self.v.file_name())
                bol = self.v.line(self.v.sel()[0].begin()).begin()
                eol = self.v.line(self.v.sel()[0].begin()).end()
                msgs = [note.message for note in relevant_notes
                        if (bol <= note.start <= eol) or (bol <= note.end <= eol)]
                self._update_statusbar("; ".join(msgs))
        else:
            self._update_statusbar(None)

    def _update_statusbar(self, status):
        sublime.set_timeout(bind(self._update_statusbar_callback, status), 100)

    def _update_statusbar_callback(self, status):
        settings = self.env.settings if self.env else sublime.load_settings("Ensime.sublime-settings")
        statusgroup = settings.get("ensime_statusbar_group", "ensime")
        status = str(status)
        if settings.get("ensime_statusbar_heartbeat_enabled", True):
            heart_beats = self.is_running()
            if heart_beats:
                def calculate_heartbeat_message():
                    def format_debugging_message(msg):
                        try:
                            return msg % (self.env.profile.name or "")
                        except:
                            return msg

                    if self.in_project():
                        if self.env.profile:
                            return format_debugging_message(
                                settings.get("ensime_statusbar_heartbeat_inproject_debugging"))
                        else:
                            return settings.get("ensime_statusbar_heartbeat_inproject_normal")
                    else:
                        if self.env.profile:
                            return format_debugging_message(
                                settings.get("ensime_statusbar_heartbeat_notinproject_debugging"))
                        else:
                            return settings.get("ensime_statusbar_heartbeat_notinproject_normal")

                heartbeat_message = calculate_heartbeat_message()
                if heartbeat_message:
                    heartbeat_message = heartbeat_message.strip()
                    if not status:
                        status = heartbeat_message
                    else:
                        heartbeat_joint = settings.get("ensime_statusbar_heartbeat_joint")
                        status = heartbeat_message + heartbeat_joint + status
        if status:
            maxlength = settings.get("ensime_statusbar_maxlength", 150)
            if len(status) > maxlength:
                status = status[0:maxlength] + "..."
            self.v.set_status(statusgroup, status)
        else:
            self.v.erase_status(statusgroup)

    def redraw_breakpoints(self):
        self.v.erase_regions(ENSIME_BREAKPOINT_REGION)
        if self.v.is_loading():
            sublime.set_timeout(self.redraw_breakpoints, 100)
        else:
            if self.env:
                relevant_breakpoints = [breakpoint for breakpoint in self.env.breakpoints if same_paths(
                    breakpoint.file_name, self.v.file_name())]
                regions = [self.v.full_line(self.v.text_point(breakpoint.line - 1, 0))
                           for breakpoint in relevant_breakpoints]
                self.v.add_regions(
                    ENSIME_BREAKPOINT_REGION,
                    regions,
                    self.env.settings.get("breakpoint_scope"),
                    self.env.settings.get("breakpoint_icon"),
                    sublime.HIDDEN)
                # sublime.DRAW_OUTLINED)

    def redraw_debug_focus(self):
        self.v.erase_regions(ENSIME_DEBUGFOCUS_REGION)
        if self.v.is_loading():
            sublime.set_timeout(self.redraw_debug_focus, 100)
        else:
            if self.env and self.env.focus and same_paths(self.env.focus.file_name, self.v.file_name()):
                focused_region = self.v.full_line(self.v.text_point(self.env.focus.line - 1, 0))
                self.v.add_regions(
                    ENSIME_DEBUGFOCUS_REGION,
                    [focused_region],
                    self.env.settings.get("debugfocus_scope"),
                    self.env.settings.get("debugfocus_icon"))
                w = self.v.window() or sublime.active_window()
                w.focus_view(self.v)
                self.redraw_breakpoints()
                sublime.set_timeout(bind(self._scroll_viewport, self.v, focused_region), 0)

    def _scroll_viewport(self, v, region):
        # thanks to Fredrik Ehnbom
        # see https://github.com/quarnster/SublimeGDB/blob/master/sublimegdb.py
        # Shouldn't have to call viewport_extent, but it
        # seems to flush whatever value is stale so that
        # the following set_viewport_position works.
        # Keeping it around as a WAR until it's fixed
        # in Sublime Text 2.
        v.viewport_extent()
        # v.set_viewport_position(data, False)
        v.sel().clear()
        v.sel().add(region.begin())
        v.show(region)

    def redraw_stack_focus(self):
        self.v.erase_regions(ENSIME_STACKFOCUS_REGION)
        if self.env and self.env.stackframe and self.v.name() == ENSIME_STACK_VIEW:
            focused_region = self.v.full_line(self.v.text_point(self.env.stackframe.index, 0))
            self.v.add_regions(
                ENSIME_STACKFOCUS_REGION,
                [focused_region],
                self.env.settings.get("stackfocus_scope"),
                self.env.settings.get("stackfocus_icon"))


class Completer(EnsimeEventListener):
    def _signature_doc(self, sig):
        """Given a ensime CompletionSignature structure, returns a short
        string suitable for showing in the help section of the completion
        pop-up."""
        sections = sig.sections
        section_param_strs = [[param[1] for param in params] for params in sections]
        section_strs = ["(" + ", ".join(tpes) + ")" for tpes in
                        section_param_strs]
        return "".join(section_strs) + ": " + sig.result

    def _signature_snippet(self, sig):
        """Given a ensime CompletionSignature structure, returns a Sublime Text
        snippet describing the method parameters."""

        sections = sig.sections
        section_snippets = []
        i = 1
        for params in sections:
            param_snippets = []
            for param in params:
                name, tpe = param
                param_snippets.append("${%s:%s:%s}" % (i, name, tpe))
                i += 1
            section_snippets.append("(" + ", ".join(param_snippets) + ")")
        return "".join(section_snippets)

    def _completion_response(self, ensime_completions):
        """Transform list of completions from ensime API to a the structure
        necessary for returning to sublime API."""
        return ([(c.name + "\t" + self._signature_doc(c.signature),
                  c.name + self._signature_snippet(c.signature))
                 for c in ensime_completions.completions],
                sublime.INHIBIT_EXPLICIT_COMPLETIONS |
                sublime.INHIBIT_WORD_COMPLETIONS)

    def _query_completions(self, prefix, locations):
        """Query the ensime API for completions. Note: we must ask for _all_
        completions as sublime will not re-query unless this query returns an
        empty list."""
        # Short circuit for prefix that is known to return empty list
        # TODO(aemoncannon): Clear ignore prefix if the user
        # moves point to new context.
        if (self.env.completion_ignore_prefix and
                prefix.startswith(self.env.completion_ignore_prefix)):
            return self._completion_response(CompletionInfoList.create(prefix, []))
        else:
            self.env.completion_ignore_prefix = None

        if self.v.is_dirty():
            source_file_info = SourceFileInfo(self.v.file_name(), self.v.substr(Region(0, self.v.size())))
        else:
            source_file_info = SourceFileInfo(self.v.file_name())

        completions = self.rpc.completions(source_file_info, locations[0], 100, False, False)
        if not completions:
            self.env.completion_ignore_prefix = prefix
            return self._completion_response(CompletionInfoList.create(prefix, []))
        else:
            return self._completion_response(completions)

    def on_query_completions(self, prefix, locations):
        if self.env.running and self.in_project():
            return self._query_completions(prefix, locations)
        else:
            return []


# ############################# SUBLIME COMMANDS: MAINTENANCE ##############################

class EnsimeStartup(EnsimeWindowCommand):
    def is_enabled(self):
        return bool(self.env and not self.env.running)

    def run(self):
        # refreshes the config (fixes #29)
        self.env.recalc()

        if not self.env.project_config:
            (_, _, error_handler) = dotensime.load(self.w)
            error_handler()
            return

        self.env.controller = Controller(self.env)
        self.env.controller.startup()


class EnsimeShutdown(RunningOnly, EnsimeWindowCommand):
    def run(self):
        self.env.controller.shutdown()


class EnsimeRestart(RunningOnly, EnsimeWindowCommand):
    def run(self):
        self.w.run_command("ensime_shutdown")
        sublime.set_timeout(bind(self.w.run_command, "ensime_startup"), 100)


class EnsimeShowProject(ProjectExists, EnsimeWindowCommand):
    def run(self):
        dotensime.edit(self.w)


class EnsimeShowSession(EnsimeWindowCommand):
    def is_enabled(self):
        return self.is_valid()

    def run(self):
        dotsession.edit(self.env)


def _show_log(self):
    log = self.env.log_file
    line = 1
    try:
        with open(log) as f:
            line = len(f.readlines())
    except:
        pass
    self.w.open_file("%s:%d:%d" % (log, line, 1), sublime.ENCODED_POSITION)


class EnsimeShowLog(EnsimeWindowCommand):
    def is_enabled(self):
        return self.is_valid()

    def run(self):
        _show_log(self)


class EnsimeHighlight(RunningOnly, EnsimeWindowCommand):
    def run(self, enable=True):
        self.env.settings.set("error_highlight", not not enable)
        sublime.save_settings("Ensime.sublime-settings")
        self.colorize_all()


# ############################# SUBLIME COMMANDS: DEVELOPMENT ##############################

class EnsimeShowNotes(EnsimeWindowCommand):
    def is_enabled(self):
        return bool(self.env and self.env.notes.can_show())

    def run(self):
        self.env.notes.show()


class Notes(EnsimeToolView):
    def can_show(self):
        return self.is_running() and self.in_project(self.w.active_view())

    @property
    def name(self):
        return ENSIME_NOTES_VIEW

    def clear(self):
        self.env.notee = None
        super(Notes, self).clear()

    def render(self):
        lines = []
        if self.env.notee:
            relevant_notes = self.env.notes_storage.for_file(self.env.notee.file_name())
            for note in relevant_notes:
                loc = self.project_relative_path(note.file_name) + ":" + str(note.line)
                severity = note.severity
                message = note.message
                diagnostics = ": ".join(str(x) for x in [loc, severity, message])
                lines += [diagnostics]
                lines += [self.env.notee.substr(self.env.notee.line(note.start))]
                lines += [" " * (note.col - 1) + "^"]
        return "\n".join(lines)


class EnsimeHandleSymbolInfo(EnsimeCommon):
    def handle_symbol_info(self, info):
        if not self.handle_symbol_info_inner(info):
            #retry once
            self.status_message("Please wait, trying harder to locate " + (str(info.name) if info else "symbol"))
            self.rpc.typecheck_all(self.typecheck_all_finished)
            pos = int(self.v.sel()[0].begin())
            self.rpc.symbol_at_point(self.v.file_name(), pos, self.handle_symbol_info_no_retry)

    def typecheck_all_finished(self, msg_id):
        self.status_message("Full type check completed")

    def handle_symbol_info_no_retry(self, info):
        if not self.handle_symbol_info_inner(info):
            self.v.run_command("goto_definition")

    def handle_symbol_info_inner(self, info):
        if info and info.decl_pos:
            # fails from time to time, because sometimes self.w is None
            # v = self.w.open_file(info.decl_pos.file_name)

            # <the first attempt to make it work, gave rise to #31>
            # v = sublime.active_window().open_file(info.decl_pos.file_name)
            # # <workaround 1> this one doesn't work, because of the pervasive problem with `show`
            # # v.sel().clear()
            # # v.sel().add(Region(info.decl_pos.offset, info.decl_pos.offset))
            # # v.show(info.decl_pos.offset)
            # # <workaround 2> this one ignores the second open_file
            # # row, col = v.rowcol(info.decl_pos.offset)
            # # sublime.active_window().open_file("%s:%d:%d" % (info.decl_pos.file_name, row + 1, col + 1),
            # # sublime.ENCODED_POSITION)

            file_name = info.decl_pos.file_name
            contents = None
            with open(file_name, "rb") as f:
                contents = f.read().decode("utf8")
            if contents:
                # todo. doesn't support mixed line endings
                def detect_newline():
                    if "\n" in contents and "\r" in contents:
                        return "\r\n"
                    if "\n" in contents:
                        return "\n"
                    if "\r" in contents:
                        return "\r"
                    return None

                if info.decl_pos.is_offset:
                    zb_offset = info.decl_pos.offset
                    newline = detect_newline()
                    zb_row = contents.count(newline, 0, zb_offset) if newline else 0
                    zb_col = zb_offset - contents.rfind(newline, 0, zb_offset) - len(newline) if newline else zb_offset
                else:
                    zb_row = info.decl_pos.line
                    zb_col = 0

                def open_file():
                    return self.w.open_file("%s:%d:%d" % (file_name, zb_row + 1, zb_col + 1), sublime.ENCODED_POSITION)

                # w = self.w or sublime.active_window()
                # g, i = (None, None)
                if self.v is not None and same_paths(self.v.file_name(), file_name):
                    # open_file doesn't work, so we have to work around
                    # open_file()

                    # <workaround 1> close and then reopen
                    # works fine but is hard on the eyes
                    # g, i = w.get_view_index(self.v)
                    # self.v.run_command("save")
                    # self.w.run_command("close_file")
                    # v = open_file()
                    # self.w.set_view_index(v, g, i)

                    # <workaround 2> v.show
                    # has proven to be very unreliable
                    # but let's try and use it
                    offset_in_editor = self.v.text_point(zb_row, zb_col)
                    region_in_editor = Region(offset_in_editor, offset_in_editor)
                    sublime.set_timeout(bind(self._scroll_viewport, self.v, region_in_editor), 100)
                    return True
                else:
                    open_file()
                    return True
            else:
                self.status_message("Cannot open " + file_name)
                return True
        else:
            self.status_message("Cannot locate " + (str(info.name) if info else "symbol"))
            return False

    def _scroll_viewport(self, v, region):
        v.sel().clear()
        v.sel().add(region.begin())
        v.show(region)


class EnsimeInspectType:
    tuple_regex = re.compile("^Tuple\d+")

    def format_param(self, param, begin, end, is_tooltip):
        res = "{0}: <a href={1}>{2}</a>".format(
            html.escape(param.param_name),
            html.escape(param.param_type.full_name),
            html.escape(param.param_type.name)
        )
        if param.param_type.type_args:
            res += begin + ", ".join([self.parse_tpe(t, is_tooltip) for t in param.param_type.type_args]) + end
        return res

    def format_param_list(self, param_section, begin, end, is_tooltip):
        return "({0}{1})".format(
            "implicit " if param_section.is_implicit else "",
            ", ".join([self.format_param(p, begin, end, is_tooltip) for p in param_section.params])
        )

    # is_tooltip param is a boolean which determines if either a status_message string
    # or tooltip is generated
    def parse_tpe(self, tpe, is_tooltip):
        if tpe and tpe.name != "<notype>":
            if tpe.arrow_type:
                param_sections = tpe.param_sections
                type_info = tpe.result_type
            else:
                param_sections = []
                type_info = tpe

            type_desc = tpe.name

            if EnsimeInspectType.tuple_regex.match(type_info.name):
                begin, end = '(', ')'
                res = ""
            else:
                begin, end = '[', ']'
                full_name, name = type_info.full_name, type_info.name
                if is_tooltip:
                    # grab any type args from the description first
                    type_args = "" if type_desc[0] != '[' else html.escape(type_desc[0:type_desc.find('](') + 1])
                    param_section_list = "".join([self.format_param_list(ps, begin, end, is_tooltip)
                                                  for ps in param_sections])
                    res = "<a href={0}>{1}</a>".format(html.escape(full_name), html.escape(name))
                    if param_section_list:
                        res = "{0}{1}: {2}".format(type_args, param_section_list, res)
                else:
                    res = name
                    last_paren = type_desc.rfind(')')
                    type_desc_sans_return = type_desc[0:last_paren+1]
                    if type_desc_sans_return:
                        res = "{0}: {1}".format(type_desc_sans_return, res)

            if type_info.type_args:
                res += begin + ", ".join([self.parse_tpe(t, is_tooltip) for t in type_info.type_args]) + end

            return res

        return None


class EnsimeInspectTypeAtPointTooltip(RunningProjectFileOnly, EnsimeTextCommand, EnsimeHandleSymbolInfo,
                                      EnsimeInspectType):
    def run(self, edit, target=None):
        pos = int(target or self.v.sel()[0].begin())
        self.rpc.type_at_point(self.v.file_name(), pos, self.handle_reply)

    def handle_reply(self, tpe):
        self.logger.info("EnsimeInspectTypeTooltip.handleReply: " + str(tpe))
        markup = self.parse_tpe(tpe, is_tooltip=True)
        if tpe:
            font_size = sublime.load_settings("Preferences.sublime-settings").get("font_size", 14)
            self.w.active_view().show_popup(
                "<div style=font-size:{0}px>{1}</div>".format(font_size, markup),
                on_navigate=bind(self.go_to_symbol),
                max_width=font_size * 80,
                max_height=font_size * 4
            )
        else:
            self.status_message("Cannot find out type")

    def go_to_symbol(self, symbol):
        self.rpc.symbol_by_name(symbol, [], [], self.handle_symbol_info)


class EnsimeInspectTypeAtPointStatus(RunningProjectFileOnly, EnsimeTextCommand, EnsimeHandleSymbolInfo,
                                     EnsimeInspectType):
    def run(self, edit, target=None):
        pos = int(target or self.v.sel()[0].begin())
        self.rpc.type_at_point(self.v.file_name(), pos, self.handle_reply)

    def handle_reply(self, tpe):
        self.logger.info("EnsimeInspectTypeStatus.handleReply: " + str(tpe))
        msg = self.parse_tpe(tpe, is_tooltip=False)
        if msg:
            self.status_message(msg)
        else:
            self.status_message("Cannot find out type")


class EnsimeBrowseScaladocAtPoint(RunningProjectFileOnly, EnsimeTextCommand):
    def run(self, edit, target=None):
        pos = int(target or self.v.sel()[0].begin())
        self.rpc.doc_uri_at_point(self.v.file_name(), pos, self.handle_reply)

    def handle_reply(self, uri):
        if uri:
            self.logger.info("EnsimeBrowseScaladocAtPoint.handleReply: " + str(uri))
            self.env.controller.client.open_uri(uri)
        else:
            self.logger.info("Doc lookup failed")
            self.status_message("Doc lookup failed")



class EnsimeGoToDefinition(RunningProjectFileOnly, EnsimeTextCommand, EnsimeHandleSymbolInfo):
    def run(self, edit, target=None):
        pos = int(target or self.v.sel()[0].begin())
        self.rpc.symbol_at_point(self.v.file_name(), pos, self.handle_symbol_info)


class EnsimeTypecheckFull(EnsimeTextCommand):
    def run(self, edit, target=None):
        self.status_message("Running full type check")
        self.rpc.typecheck_all(self.typecheck_all_finished)

    def typecheck_all_finished(self, msg_id):
        self.status_message("Full type check completed")


# common superclass for new refactoring based on diffs
class EnsimeNewRefactoring(RunningProjectFileOnly, EnsimeTextCommand):

    def refactoring_symbol(self):
        raise Exception("abstract method: EnsimeNewRefactoring.refactoring_symbol")

    def __nextRefactorId(self):
        return hash(uuid.uuid4())

    def run(self, edit, target=None):
        self._temp_edit = edit
        self._temp_target = target
        pos = int(target or self.v.sel()[0].begin())
        self._currentRefactorId = self.__nextRefactorId()
        if self.v.is_dirty():
            self.v.run_command('save')
        self.invoke_refactoring(pos)

    def handle_refactor_response(self, response):
        if response.succeeded:
            self.refactor_successful(response)
        else:
            if response.try_refresh:
                self.logger.info("Re-run requested")
                self.run(self._temp_edit, self._temp_target)
            else:
                message = "Refactor failed: " + response.reason
                self.logger.info(message)
                self.status_message(message)

    def refactor_successful(self, response):
        self.status_message("Refactoring with diff file: " + response.diff_file)
        patch_cmd = "patch -d / -p1 -i " + response.diff_file
        patch_run = os.popen(patch_cmd)
        patch_lines = patch_run.readlines()
        if patch_run.close():
            self.logger.error("Patch refactoring failed")
            self.logger.error("patch file: " + response.diff_file)
            if len(patch_lines) > 0:
                self.logger.error(patch_lines)
                error = "Refactor failed: " + patch_lines[-1]
            else:
                error = "Refactor failed: " + response.diff_file
            self.status_message(error)
        else:
            self.reload_file()
            self.logger.info("Refactoring succeeded, patch file: " + response.diff_file)
            self.status_message("Refactoring succeeded")

    def reload_file(self):
        view = self.v
        original_size = view.size()
        original_pos = view.sel()[0].begin()
        # Load changes
        view.run_command('revert')
        # Wait until view loaded then move cursor to original position        
      
        def on_load():
            if view.is_loading():
                # Wait again
                set_timeout(on_load, 50)
            else:
                size_diff = view.size() - original_size 
                new_pos = original_pos + size_diff
                view.sel().clear()
                view.sel().add(sublime.Region(new_pos))
                view.show(new_pos)
            self.v.sel().clear()
        
        on_load()


class EnsimeAddImport(EnsimeNewRefactoring):

    def refactoring_symbol(self):
        return 'addImport'

    def invoke_refactoring(self, pos):
        word = self.v.substr(self.v.word(pos))
        if len(word.strip()) > 0:
            self.rpc.import_suggestions(self.v.file_name(), pos, [word],
                                        self.env.settings.get("max_import_suggestions", 20),
                                        self.handle_sugestions_response)

    def handle_sugestions_response(self, info):
        # We only send one word in the request so there should only be one SymbolSearchResults in the response list
        results = info[0].results
        names = [a.name for a in results]

        def do_refactor(i):
            if i > -1:
                params = [sym('refactorType'), self.refactoring_symbol(), sym('qualifiedName'), names[i],
                          sym('file'), self.v.file_name(), sym('start'), 0, sym('end'), 0]
                self.rpc.diff_refactor(self._currentRefactorId, params, False, self.handle_refactor_response)

        self.v.window().show_quick_panel(names, do_refactor)


class EnsimeOrganizeImports(EnsimeNewRefactoring):

    def refactoring_symbol(self):
        return 'organizeImports'

    def invoke_refactoring(self, pos):
        params = [sym('refactorType'), self.refactoring_symbol(), sym('file'), self.v.file_name()]
        self.rpc.diff_refactor(self._currentRefactorId, params, False, self.handle_refactor_response)


class EnsimeInlineLocal(EnsimeNewRefactoring):

    def refactoring_symbol(self):
        return 'inlineLocal'

    def invoke_refactoring(self, pos):
        word = self.v.substr(self.v.word(pos))
        params = [sym('refactorType'), self.refactoring_symbol(),
                  sym('file'), self.v.file_name(), sym('start'), pos, sym('end'), pos + len(word)]
        self.rpc.diff_refactor(self._currentRefactorId, params, False, self.handle_refactor_response)


class EnsimeExtractRefactoring(EnsimeNewRefactoring):

    def invoke_refactoring(self, pos):
        regions = [r for r in self.v.sel()]
        if len(regions) == 1:
            region = regions[0]
            if region.begin() == region.end():
                self.status_message('Please select a region to extract')
            else:
                self.__region_begin = region.begin()
                self.__region_end = region.end()
                self.w.show_input_panel(self.extract_prompt_message(), '',
                                        self.extract_it, None, None)
        else:
            self.status_message('Select a single region to extract')

    def extract_it(self, arg):
        params = [sym('refactorType'), self.refactoring_symbol(),
                  self.extract_sym(), arg, sym('file'), self.v.file_name(),
                  sym('start'), self.__region_begin, sym('end'), self.__region_end]
        self.rpc.diff_refactor(self._currentRefactorId, params, False, self.handle_refactor_response)


class EnsimeRename(EnsimeNewRefactoring):

    def refactoring_symbol(self):
        return 'rename'

    def invoke_refactoring(self, pos):
        self._word = self.v.substr(self.v.word(pos))
        self._pos = pos
        self.w.show_input_panel("New name:", '', self.rename_it, None, None)

    def rename_it(self, arg):
        params = [sym('refactorType'), self.refactoring_symbol(),
                  sym('newName'), arg, sym('file'), self.v.file_name(),
                  sym('start'), self._pos, sym('end'), self._pos + len(self._word)]
        self.rpc.diff_refactor(self._currentRefactorId, params, False, self.handle_refactor_response)

class EnsimeRenameRefactoring(EnsimeExtractRefactoring):
    def refactoring_symbol(self):
        return 'rename'

    def extract_prompt_message(self):
        return 'Rename: '

    def extract_sym(self):
        return sym('newName')

class EnsimeExtractLocal(EnsimeExtractRefactoring):
    def refactoring_symbol(self):
        return 'extractLocal'

    def extract_prompt_message(self):
        return 'Extracted val name: '

    def extract_sym(self):
        return sym('name')


class EnsimeExtractMethod(EnsimeExtractRefactoring):
    def refactoring_symbol(self):
        return 'extractMethod'

    def extract_prompt_message(self):
        return 'Extracted method name: '

    def extract_sym(self):
        return sym('methodName')


class EnsimeBuild(ProjectExists, EnsimeWindowCommand):
    def run(self):
        cmd = sbt_command("compile")  # TODO: make this configurable
        if cmd:
            self.w.run_command("exec", {"cmd": cmd, "working_dir": self.env.project_root})


# ############################# SUBLIME COMMANDS: DEBUGGING ##############################

class EnsimeToggleBreakpoint(ProjectFileOnly, EnsimeTextCommand):
    def run(self, edit):
        file_name = self.v.file_name()
        if file_name and len(self.v.sel()) == 1:
            zb_line, _ = self.v.rowcol(self.v.sel()[0].begin())
            line = zb_line + 1
            old_breakpoints = self.env.breakpoints
            new_breakpoints = [b for b in self.env.breakpoints
                               if not (same_paths(b.file_name, file_name) and b.line == line)]
            if len(old_breakpoints) == len(new_breakpoints):
                # add
                new_breakpoints.append(dotsession.Breakpoint(file_name, line))
                if self.env.profile:
                    self.rpc.debug_set_break(file_name, line)
            else:
                # remove
                if self.env.profile:
                    self.rpc.debug_clear_break(file_name, line)
            self.env.breakpoints = new_breakpoints
            self.env.save_session()
            self.redraw_all_breakpoints()


class EnsimeClearBreakpoints(EnsimeWindowCommand):
    def run(self):
        self.env.load_session()
        if self.env.breakpoints and sublime.ok_cancel_dialog(
                "This will delete all breakpoints. Do you wish to continue?"):
            self.env.breakpoints = []
            if self.env.profile:
                self.rpc.clear_all_breaks()
            self.env.save_session()
            self.redraw_all_breakpoints()


class EnsimeStartDebugger(NotDebuggingOnly, EnsimeWindowCommand):
    def run(self):
        self.env.debugger.start()


class EnsimeStopDebugger(DebuggingOnly, EnsimeWindowCommand):
    def run(self):
        self.env.debugger.stop()


class EnsimeStepInto(FocusedOnly, EnsimeWindowCommand):
    def run(self):
        self.env.debugger.step_into()


class EnsimeStepOver(FocusedOnly, EnsimeWindowCommand):
    def run(self):
        self.env.debugger.step_over()


class EnsimeStepOut(FocusedOnly, EnsimeWindowCommand):
    def run(self):
        self.env.debugger.step_out()


class EnsimeContinueDebugger(FocusedOnly, EnsimeWindowCommand):
    def run(self):
        self.env.debugger.continue_()


class EnsimeSmartRunDebugger(EnsimeWindowCommand):
    def __init__(self, window):
        super(EnsimeSmartRunDebugger, self).__init__(window)
        self.startup_attempts = 0

    def is_enabled(self):
        return bool(self.env and (not self.env.profile or self.env.focus))

    def run(self):
        if not self.env.profile:
            if self.env.compiler_ready:
                self.startup_attempts = 0
                sublime.set_timeout(bind(self.w.run_command, "ensime_start_debugger"), 1000)
            else:
                self.startup_attempts += 1
                if self.startup_attempts < 10:
                    self.w.run_command("ensime_startup")
                    sublime.set_timeout(self.run, 1000)
                else:
                    self.startup_attempts = 0
        if self.env.focus:
            self.w.run_command("ensime_continue_debugger")


class EnsimeShowOutput(EnsimeWindowCommand):
    def is_enabled(self):
        return bool(self.env and self.env.output.can_show())

    def run(self):
        self.env.output.show()


class EnsimeShowStack(EnsimeWindowCommand):
    def is_enabled(self):
        return bool(self.env and self.env.stack.can_show())

    def run(self):
        self.env.stack.show()
        self.redraw_all_stack_focuses()


class EnsimeShowWatches(EnsimeWindowCommand):
    def is_enabled(self):
        return bool(self.env and self.env.watches.can_show())

    def run(self):
        self.env.watches.show()


class EnsimeDebugDoubleClick(DebuggingOnly, EnsimeTextCommand):

    def calculate_handler(self):
        view_name = self.v.name()
        if view_name == ENSIME_NOTES_VIEW:
            return self.env.notes
        elif view_name == ENSIME_OUTPUT_VIEW:
            return self.env.output
        elif view_name == ENSIME_STACK_VIEW:
            return self.env.stack
        elif view_name == ENSIME_WATCHES_VIEW:
            return self.env.watches
        else:
            return None

    def run(self, edit, target=None):
        handler = self.calculate_handler()
        if handler:
            handler.handle_event("double_click", self.v.sel()[0].a)



class Debugger(EnsimeCommon):
    def __init__(self, env_inst):
        super(Debugger, self).__init__(env_inst.w)

    def shutdown(self, erase_dashboard=False):
        self.env.profile = None
        self.env.focus = None
        self.env.backtrace = None
        self.env.stackframe = None
        self.env.watchstate = None
        if erase_dashboard:
            self.env.output.clear()
            self.env.stack.clear()
            self.env.watches.clear()

    def backup_layout(self, layout_profile):
        if self.env.settings.get("debug_autolayout"):
            layout_metadata = self.env.settings.get(layout_profile, {})
            layout_metadata["layout"] = self.w.get_layout()

            def backup_tool_layout(tool):
                if tool.v is not None:
                    g, i = self.w.get_view_index(tool.v)
                    layout_metadata[tool.name] = g
                else:
                    layout_metadata[tool.name] = None

            backup_tool_layout(self.env.stack)
            backup_tool_layout(self.env.watches)
            backup_tool_layout(self.env.output)
            self.env.settings.set(layout_profile, layout_metadata)
            sublime.save_settings("Ensime.sublime-settings")

    def apply_layout(self, layout_profile):
        if self.env.settings.get("debug_autolayout"):
            layout_metadata = self.env.settings.get(layout_profile, {})
            layout = layout_metadata.get("layout", None)
            if layout:
                self.w.set_layout(layout)

                def apply_tool_layout(tool):
                    g = layout_metadata.get(tool.name, None)
                    if g is not None:
                        v = tool.v if tool.v is not None else tool._mk_v()
                        self.w.set_view_index(v, g, 0)
                    else:
                        if tool.v is not None:
                            self.w.focus_view(tool.v)
                            self.w.run_command("close_file")
                        else:
                            pass

                apply_tool_layout(self.env.stack)
                apply_tool_layout(self.env.watches)
                apply_tool_layout(self.env.output)

    def handle(self, event):
        if event.type == "start":
            if not self.env.profile:  # avoid double initialization in the case of an attach to a suspended vm
                self.shutdown(erase_dashboard=True)
                self.env.profile = self.env.profile_being_launched
                self.backup_layout("debug_layout_when_leaving_debugmode")
                self.apply_layout("debug_layout_when_entering_debugmode")
        elif event.type == "death" or event.type == "disconnect":
            if self.env.profile:  # this condition here is just to mirror the coniditon in event.type == "start"
                self.shutdown(erase_dashboard=False)  # so that people can take a look later
                self.status_message("Debuggee has died" if event.type == "death" else "Debugger has disconnected")
                self.redraw_all_debug_focuses()
                self.redraw_all_stack_focuses()
                self.backup_layout("debug_layout_when_entering_debugmode")
                self.apply_layout("debug_layout_when_leaving_debugmode")
        elif event.type == "output":
            self.env.output.append(event.body)
        elif event.type == "exception" or event.type == "breakpoint" or event.type == "step":
            self.env.focus = Focus(event.thread_id, event.thread_name, event.file_name, event.line)
            if event.file_name and event.line:
                focus_summary = str(event.file_name) + ", line " + str(event.line)
                self.env.w.open_file("%s:%d:%d" % (self.env.focus.file_name, self.env.focus.line, 1),
                                     sublime.ENCODED_POSITION)
            else:
                focus_summary = "an unknown location"
            self.redraw_all_debug_focuses()
            self.env.stack.update_backtrace()
            if event.type == "exception":
                rendered = "an unhandled exception has been thrown: "
                rendered += (
                    str(self.rpc.debug_to_string(event.thread_id, DebugLocationReference(event.exception_id))) + "\n")
                rendered += "\n".join(["  " + line for line in self.env.stack.render().split("\n")])
                # TODO: handle double click. it won't work for output, because it lacks a stack-like handler
                self.env.output.append(rendered + "\n")
                self.env.output.show()
            self.status_message("(" + str(event.type) + ") Debugger has stopped at " + str(focus_summary))
        self.redraw_status(self.w.active_view())

    def start(self):
        launch = dotsession.load_launch(self.env)
        if launch:
            self.status_message("Starting the debugger...")
            self.env.profile_being_launched = launch

            def callback(status):
                launch_name = " " + launch.name if launch.name else ""
                if status:
                    self.status_message("Debugger has successfully started" + launch_name)
                    if launch.remote_address:
                        # we have to apply this workaround, because if we attach to a non-suspended VM
                        # then we don't get the "start" event, and the plugin will think we've not
                        # entered the debug mode
                        # TODO: fix this at the root - in Ensime
                        class FakeStartEvent(object):
                            def __init__(self):
                                self.type = "start"

                        self.handle(FakeStartEvent())
                else:
                    self.status_message("Debugger has failed to start" + launch_name + ". " + str(status.details))

            self.rpc.debug_start(launch, self.env.breakpoints, callback)
        else:
            self.status_message("Bad debug configuration")

    def stop(self):
        self.rpc.debug_stop()

    def step_into(self):
        self.rpc.debug_step(self.env.focus.thread_id)

    def step_over(self):
        self.rpc.debug_next(self.env.focus.thread_id)

    def continue_(self):
        self.rpc.debug_continue(self.env.focus.thread_id)

    def step_out(self):
        self.rpc.debug_next(self.env.focus.thread_id)


class Focus(object):
    def __init__(self, thread_id, thread_name, file_name, line):
        self.thread_id = thread_id
        self.thread_name = thread_name
        self.file_name = file_name
        self.line = line

    def __eq__(self, other):
        return (type(self) == type(other) and
                self.thread_id == other.thread_id and
                self.thread_name == other.thread_name and
                self.file_name == other.file_name and
                self.line == other.line)

    def __str__(self):
        return "%s:%s:%s:%s" % (self.thread_id, self.thread_name, self.file_name, self.line)


class Output(EnsimeToolView):
    def can_show(self):
        return not bool(self.env._output)

    @property
    def name(self):
        return ENSIME_OUTPUT_VIEW

    def clear(self):
        self.env._output = ""
        super(Output, self).clear()

    def append(self, data):
        if data:
            self.env._output += data
            if self.v is not None:
                self.v.run_command("private_tool_view_append", {'content': data})

    def render(self):
        return self.env._output


class Stack(EnsimeToolView):
    def can_show(self):
        return bool(self.env and self.env.focus)

    @property
    def name(self):
        return ENSIME_STACK_VIEW

    def clear(self):
        self.env.backtrace = None
        self.env.watches.clear()
        self._update_v("")

    def update_backtrace(self):
        # TODO: this should really be asynchronous
        # if you implement this, make sure to change correspond method signatures in rpc.py
        # to say "@async_rpc" instead of "@sync_rpc"
        # TODO: acquire backtraces of all running threads
        self.env.backtrace = self.rpc.debug_backtrace(self.env.focus.thread_id)
        self.refresh()
        self.env.watches.update_stackframe(0)

    def render(self):
        rendered = []
        for frame in self.env.backtrace.frames:
            code_location = str(frame.class_name) + "." + str(frame.method_name)
            short_file_name = frame.pc_location.file_name
            if short_file_name.startswith(self.env.project_root):
                short_file_name = short_file_name[len(self.env.project_root):]
                if short_file_name.startswith("/") or short_file_name.startswith("\\"):
                    short_file_name = short_file_name[1:]
            short_file_name = os.path.basename(
                short_file_name)  # navigation is no longer handled by result_file_regex, it now uses handle_event
            filesystem_location = str(short_file_name) + ":" + str(frame.pc_location.line)
            rendered.append(code_location + " (" + filesystem_location + ")")
        return "\n".join(rendered)

    def setup_events(self, v):
        # we don't care about arranging result_file_regex here, because we'll be using short file names
        pass

    def handle_event(self, event, target):
        if event == "double_click":
            row, _ = self.v.rowcol(target)
            if self.env and self.env.backtrace:
                frames = self.env.backtrace.frames
                if row < len(frames):
                    self.env.watches.update_stackframe(row)
                    file_name = self.env.stackframe.pc_location.file_name
                    line = self.env.stackframe.pc_location.line
                    if os.path.exists(file_name) and line != -1:
                        sel = Region(self.v.sel()[0].a, self.v.sel()[0].a)
                        self.v.sel().clear()
                        self.v.sel().add(sel)
                        # TODO: sometimes fails to position the cursor at the target line if the target file is already visible
                        self.w.open_file("%s:%d:%d" % (file_name, line, 1), sublime.ENCODED_POSITION)


class WatchNode(EnsimeCommon):
    def __init__(self, env, parent, label):
        super(WatchNode, self).__init__(env.w)
        self.parent = parent
        self.is_expanded = False
        self._children_loaded = False
        self._children = None
        self.label = label
        self._description_loaded = False
        self._description = None

    def toggle(self):
        self.is_expanded = not self.is_expanded

    def expand(self):
        self.is_expanded = True

    def collapse(self):
        self.is_expanded = False

    def load_children(self):
        raise Exception("abstract method: WatchNode.load_children")

    @property
    def children(self):
        if not self._children_loaded:
            self._children_loaded = True
            self._children = list(self.load_children())
        return self._children

    def load_description(self):
        raise Exception("abstract method: WatchNode.load_description")

    @property
    def description(self):
        if not self._description_loaded:
            self._description_loaded = True
            self._description = self.load_description()
        return self._description

    @property
    def level(self):
        return self.parent.level + 1 if self.parent else 0

    def visible_subtree(self):
        yield self
        if self.is_expanded:
            for child in self.children:
                for subsubnode in list(child.visible_subtree()):
                    yield subsubnode


class WatchValueLeaf(WatchNode):
    def __init__(self, env, parent, label, description):
        super(WatchValueLeaf, self).__init__(env, parent, label)
        self._description = description

    def load_children(self):
        return []

    def load_description(self):
        return self._description


class WatchValueReferenceNode(WatchNode):
    def __init__(self, env, parent, label, value):
        super(WatchValueReferenceNode, self).__init__(env, parent, label)
        self.value = value

    def load_description(self):
        if self.value.length != 0:
            result = self.env.rpc.debug_to_string(self.env.focus.thread_id,
                                                  DebugLocationReference(self.value.object_id))
            result = result if result is not False and result is not None else "<failed to evaluate>"
            return result
        else:
            return "[]"

    def load_children(self):
        if self.is_show_class():
            yield WatchValueLeaf(self.env, self, "class", self.value.type_name)
        for child_like in self.enumerate_children():
            if type(child_like) == tuple:
                key, value = child_like
                yield create_watch_value_node(self.env, self, key, value)
            else:
                child = child_like
                yield child

    def is_show_class(self):
        return self.env.settings.get("debug_show_class")

    def enumerate_children(self):
        raise Exception("abstract method: WatchValueReferenceNode.enumerate_children")


class WatchValueCollectionNode(WatchValueReferenceNode):
    def __init__(self, env, parent, label, value, start):
        super(WatchValueCollectionNode, self).__init__(env, parent, label, value)
        self.start = start

    def is_show_class(self):
        return self.env.settings.get("debug_show_class") and self.start == 0

    def enumerate_children(self):
        threshold = self.env.settings.get("debug_max_collection_elements_to_show", 0)
        for i, (key, value) in enumerate(self.enumerate_elements()):
            if i == threshold and threshold > 0:
                num_delayed = self.number_of_elements - i - self.start
                delayed = self.shift(i)
                quantifier = "element" if num_delayed == 1 else "elements"
                delayed._description_loaded = True
                delayed._description = "<" + str(num_delayed) + " more " + quantifier + ">"
                yield delayed
                return
            yield (key, value)

    @property
    def shift(self, start):
        raise Exception("abstract method: WatchValueCollectionNode.shift")

    @property
    def number_of_elements(self):
        raise Exception("abstract method: WatchValueCollectionNode.number_of_elements")

    def enumerate_elements(self):
        raise Exception("abstract method: WatchValueCollectionNode.enumerate_elements")


class WatchValueArrayNode(WatchValueCollectionNode):
    def __init__(self, env, parent, label, value, start=0):
        super(WatchValueArrayNode, self).__init__(env, parent, label, value, start)

    def shift(self, start):
        return WatchValueArrayNode(self.env, self, "more", self.value, self.start + start)

    @property
    def number_of_elements(self):
        return self.value.length

    def enumerate_elements(self):
        for i in range(self.start, self.value.length):
            key = "[" + str(i) + "]"
            value = self.rpc.debug_value(DebugLocationElement(self.value.object_id, i))
            yield (key, value)


class WatchValueObjectNode(WatchValueReferenceNode):
    def __init__(self, env, parent, label, value):
        super(WatchValueObjectNode, self).__init__(env, parent, label, value)

    def enumerate_children(self):
        for field in self.value.fields:
            key = field.name
            value = self.rpc.debug_value(DebugLocationField(self.value.object_id, field.name))
            yield (key, value)


def create_watch_value_node(env, parent, label, value):
    if str(value.type) == "null":
        return WatchValueLeaf(env, parent, label, "null")
    elif str(value.type) == "prim":
        return WatchValueLeaf(env, parent, label, value.summary)
    elif str(value.type) == "str":
        return WatchValueLeaf(env, parent, label, value.summary)
    elif str(value.type) == "obj":
        def is_scala_collection(type_name):
            return type_name == "scala.collection.immutable.$colon$colon"

        settings = sublime.load_settings("Ensime.sublime-settings")
        if settings.get("debug_specialcase_scala_collections") and is_scala_collection(value.type_name):
            # TODO: implement reflective invocation API in Ensime and revisit this
            # manifest_any = <get Manifest.Any>
            # equivalent_array = <invoke value.toString(classtag_anyref)>
            # return WatchValueArrayNode(env, parent, label, equivalentArray)
            return WatchValueObjectNode(env, parent, label, value)
        else:
            return WatchValueObjectNode(env, parent, label, value)
    elif str(value.type) == "arr":
        return WatchValueArrayNode(env, parent, label, value)
    else:
        raise Exception("unexpected debug value of type " + str(value.type) + ": " + str(value))


class WatchRoot(WatchNode):
    def __init__(self, env):
        super(WatchRoot, self).__init__(env, None, None)
        self.expand()

    def load_children(self):
        if self.env.stackframe:
            if self.env.stackframe.this_object_id != "-1":  # supposedly, this stands for "invalid value"
                value = self.rpc.debug_value(DebugLocationReference(self.env.stackframe.this_object_id))
                yield create_watch_value_node(self.env, self, "this", value)
            for i, local in enumerate(self.env.stackframe.locals):
                label = local.name
                # TODO: this, along with other stuff in WatchValueNode, should really be asynchronous
                # if you implement this, make sure to change correspond method signatures in rpc.py
                # to say "@async_rpc" instead of "@sync_rpc"
                value = self.rpc.debug_value(
                    DebugLocationSlot(self.env.backtrace.thread_id, self.env.stackframe.index, i))
                yield create_watch_value_node(self.env, self, label, value)


class Watches(EnsimeToolView):
    def can_show(self):
        return bool(self.env and self.env.focus)

    @property
    def name(self):
        return ENSIME_WATCHES_VIEW

    def clear(self):
        self.env.stackframe = None
        self.env.watchstate = None
        self._update_v("")

    def update_stackframe(self, index):
        self.env.stackframe = self.env.backtrace.frames[index] if self.env.backtrace else None
        self.env.watchstate = WatchRoot(self.env)
        self.redraw_all_stack_focuses()
        self.refresh()

    @property
    def nodes(self):
        return list(self.env.watchstate.visible_subtree())[1:]  # strip off the root itself

    def render(self):
        rendered = []
        if self.env.watchstate:
            def render_node(node):
                return "  " * (node.level - 1) + str(node.label) + " = " + str(node.description)

            rendered.extend(list(map(render_node, self.nodes)))
        return "\n".join(rendered)

    def setup_events(self, v):
        # we don't care about arranging result_file_regex here, because we want to use double-click to expand watchees
        pass

    def handle_event(self, event, target):
        if event == "double_click":
            row, _ = self.v.rowcol(target)
            if row < len(self.nodes):
                self.nodes[row].toggle()
            self.refresh()
            sublime.set_timeout(self.clear_sel, 0)

    def clear_sel(self):
        self.v.sel().clear()

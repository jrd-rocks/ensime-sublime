import sublime
import threading
from uuid import uuid4

from . import dotensime, dotsession
from . import sexp
from .paths import *


envLock = threading.RLock()
ensime_envs = {}


def for_window(window):
    if window:
        window_key = (window.folders() or [window.id()])[0]
        if window_key in ensime_envs:
            return ensime_envs[window_key]
        envLock.acquire()
        try:
            if not (window_key in ensime_envs):
                # protection against reentrant EnsimeEnvironments
                ensime_envs[window_key] = None
                try:
                    ensime_envs[window_key] = EnsimeEnvironment(window)
                    print("Created ensime environment for ", window_key)
                except:
                    print("No ensime environment for ", window_key)
            else:
                print("Found existing ensime environment for ", window_key)

            return ensime_envs[window_key]
        finally:
            envLock.release()
    return None


class NoteStorage(object):
    def __init__(self):
        self.data = []
        self.normalized_cache = {}
        self.per_file_cache = {}

    def append(self, data):
        self.data += data
        for datum in data:
            if datum.file_name not in self.normalized_cache:
                self.normalized_cache[datum.file_name] = normalize_path(datum.file_name)
            file_name = self.normalized_cache[datum.file_name]
            if file_name not in self.per_file_cache:
                self.per_file_cache[file_name] = []
            self.per_file_cache[file_name].append(datum)

    def filter(self, pred):
        dropouts = set([self.normalized_cache[n.file_name] for n in [n for n in self.data if not pred(n)]])
        # doesn't take into account pathological cases when a "*.scala" file
        # is actually a symlink to something without a ".scala" extension
        for file_name in list(self.per_file_cache):
            if file_name in dropouts:
                del self.per_file_cache[file_name]
        self.data = list(filter(pred, self.data))

    def clear(self):
        self.filter(lambda f: False)

    def for_file(self, file_name):
        if file_name not in self.normalized_cache:
            self.normalized_cache[file_name] = normalize_path(file_name)
        file_name = self.normalized_cache[file_name]
        if file_name not in self.per_file_cache:
            self.per_file_cache[file_name] = []
        return self.per_file_cache[file_name]


class EnsimeEnvironment(object):
    def __init__(self, window):
        self.valid = False
        self.settings = None
        self.running = False
        self.logger = None
        self.breakpoints = []
        self.w = window
        self.recalc()  # might only see empty window.folders(), so initialized values will be bogus
        sublime.set_timeout(self.__deferred_init__, 500)


    def __deferred_init__(self):
        self.recalc()
        from .ensime import Daemon

        v = self.w.active_view()
        if v is not None:
            Daemon(v).on_activated()  # recolorize

    @property
    def project_root(self):
        return decode_path(self._project_root)

    @property
    def project_config(self):
        config = self._project_config
        if self.settings.get("os_independent_paths_in_dot_ensime"):
            if type(config) == list:
                i = 0
                while i < len(config):
                    key = config[i]
                    literal_keys = [":root-dir", ":target"]
                    list_keys = [":compile-deps", ":compile-jars", ":runtime-deps", ":runtime-jars", ":test-deps",
                                 ":sources", ":reference-source-roots"]
                    if str(key) in literal_keys:
                        config[i + 1] = decode_path(config[i + 1])
                    elif str(key) in list_keys:
                        config[i + 1] = [decode_path(path) for path in config[i + 1]]
                    else:
                        pass
                    i += 2
        return config

    @property
    def session_file(self):
        return (self.project_root + os.sep + ".ensime_session") if self.project_root else None

    def create_logger(self, debug, log_file):
        import logging
        logger = logging.getLogger("ensime")
        file_log_formatter = logging.Formatter("%(asctime)s [%(levelname)-5.5s]  %(message)s")
        console_log_formatter = logging.Formatter("[Ensime] %(asctime)s [%(levelname)-5.5s]  %(message)s")

        logger.handlers.clear()
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(file_log_formatter)
        logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(console_log_formatter)
        logger.addHandler(console_handler)

        if debug:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)

        logger.info("New Logger initialised")
        return logger

    def recalc(self):
        # plugin-wide stuff (immutable)
        self.settings = sublime.load_settings("Ensime.sublime-settings")
        debug = self.settings.get("debug", False)

        # instance-specific stuff (immutable)
        (root, conf, _) = dotensime.load(self.w)
        self._project_root = root
        self._project_config = conf
        self.dotensime_file = os.path.join(self.project_root, ".ensime")
        self.valid = self.project_config is not None

        self.config_map = sexp.sexp_to_key_map(self.project_config)

        self.cache_dir = self.config_map.get(":cache-dir")

        from .ensime import mkdir_p

        # ensure the cache_dir exists otherwise log initialisation will fail
        mkdir_p(self.cache_dir)

        self.log_file = os.path.join(self.cache_dir, "ensime.log")

        if self.logger is None:
            self.logger = self.create_logger(debug, self.log_file)

        # system stuff (mutable)
        self.session_id = uuid4()
        self.running = False
        self.controller = None  # injected by EnsimeStartup to ensure smooth reloading
        self.compiler_ready = False

        # core stuff (mutable)
        self.notes_storage = NoteStorage()
        self.notee = None
        # Tracks the most recent completion prefix that has been shown to yield empty
        # completion results. Use this so we don't repeatedly hit ensime for results
        # that don't exist.
        self.completion_ignore_prefix = None

        # debugger stuff (mutable)
        # didn't prefix it with "debugger_", because there are no name clashes yet
        self.profile_being_launched = None
        self.profile = None  # launch config used in current debug session
        self.breakpoints = []
        self.focus = None
        self.backtrace = None
        self.stackframe = None
        self.watchstate = None
        self._output = ""

        # load the session (if exists)
        self.load_session()

    # the guys below are made to be properties
    # because we do want to encapsulate them in objects
    # however doing that will prevent smooth development
    # if we put an object instance into a field, then it won't be reloaded by Sublime
    # when the corresponding source file is changed

    # this leads to a funny model, when env contains all shared state
    # and objects outside env are just bunches of pure functions that carry state around
    # state weaving is made implicit by the EnsimeCommon base class, but it's still there

    @property
    def rpc(self):
        from .rpc import Rpc

        return Rpc(self)

    @property
    def notes(self):
        from .ensime import Notes

        return Notes(self)

    @property
    def debugger(self):
        from .ensime import Debugger

        return Debugger(self)

    @property
    def output(self):
        from .ensime import Output

        return Output(self)

    @property
    def stack(self):
        from .ensime import Stack

        return Stack(self)

    @property
    def watches(self):
        from .ensime import Watches

        return Watches(self)

    # externalizable part of mutable state

    def load_session(self):
        session = dotsession.load(self)
        if session:
            self.breakpoints = session.breakpoints
        return session

    def save_session(self):
        session = dotsession.load(self) or dotsession.Session(breakpoints=[], launches=[], launch_key=None)
        session.breakpoints = self.breakpoints
        dotsession.save(self, session)

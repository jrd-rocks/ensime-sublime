import sublime

import os
import threading
import logging
from logging import FileHandler
from functools import partial as bind
import datetime

import dotensime
from util import Util
from notes import NotesStorage
from editor import Editor
from config import LOG_FORMAT, CONSOLE_LOG_FORMAT

env_lock = threading.RLock()
# dictionary from window to it's EnsimeEnvironment
ensime_envs = {}


def getEnvironment(window):
    """Return the EnsimeEnvironment for the window if it's valid,
    else return None."""
    if window:
        env = None
        window_key = (window.folders() or [window.id()])[0]
        if window_key in ensime_envs:
            env_for_key = ensime_envs[window_key]
            if env_for_key.valid:
                env = env_for_key
        return env
    else:
        return None


def getOrCreateNew(window):
    if window:
        window_key = (window.folders() or [window.id()])[0]
        # it may no longer have the .ensime file or it might have changed
        # check for no .ensime and bad config done in recalc()
        if window_key in ensime_envs:
            return ensime_envs[window_key]
        env_lock.acquire()
        try:
            if not (window_key in ensime_envs):
                # protection against reentrant EnsimeEnvironments
                ensime_envs[window_key] = None
                try:
                    ensime_envs[window_key] = _EnsimeEnvironment(window)
                    print("Created ensime environment for ", window_key)
                except Exception as e:
                    print("""No ensime environment for {window}.
Raised an error : {err}""".format(window=window_key, err=e))
            else:
                print("Found existing ensime environment for ", window_key)

            return ensime_envs[window_key]
        finally:
            env_lock.release()
    return None


class _EnsimeEnvironment(object):
    """An Ensime Environment for a scala project.

    Every commmand requires an EnsimeEnvironment instance which is obtained through
    getOrCreateNew. It contains the config map and loggger which can then be used for
    further tasks."""
    def __init__(self, window):
        self.window = window
        self.logger = None
        self.valid = False
        self.notes_storage = None
        self.editor = None
        self.client = None
        # Not valid when created, you must call recalc while starting up Ensime
        # self.recalc()

    def create_logger(self, debug, log_file):
        logger = logging.getLogger("ensime")
        file_log_formatter = logging.Formatter(LOG_FORMAT)
        console_log_formatter = logging.Formatter(CONSOLE_LOG_FORMAT)

        logger.handlers.clear()
        with open(log_file, "w") as f:
            now = datetime.datetime.now()
            tm = now.strftime("%Y-%m-%d %H:%M:%S.%f")
            f.write("{}: {} - {}\n".format(tm, "Initializing project", self.project_root))
        file_handler = FileHandler(log_file)
        file_handler.setFormatter(file_log_formatter)
        logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(console_log_formatter)
        logger.addHandler(console_handler)

        if debug:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)

        logger.info("Logger initialised.")
        return logger

    def recalc(self):
        """Recalculates the ensime environment variables and return True if
        if successfull else raises an exception.
        Calls dotensime.load for loading .ensime config which might
        raise error if config is not found or cannot be parsed.
        It also :
            Creates the cache-dir if it doesn't already exist.
            Create the logger.
            Resets the client.
        """
        # plugin-wide stuff (immutable)
        self.settings = sublime.load_settings("Ensime.sublime-settings")
        debug = self.settings.get("debug", False)

        # for better experience
        s = sublime.load_settings("Preferences.sublime-settings")
        self.previous_auto_complete = s.get("auto_complete", True)
        s.set("auto_complete", False)
        self.previous_show_definitions = s.get("show_definitons", True)
        s.set("show_definitions", False)
        sublime.save_settings("Preferences.sublime-settings")

        # initialize parameters ()
        self.config = dotensime.load(self.window)
        self.valid = self.config is not None
        self.project_root = self.config['root-dir']
        self.notes_storage = NotesStorage()
        self.cache_dir = self.config['cache-dir']
        self.editor = Editor(self.window, self.settings, self.notes_storage)
        self.client = None
        # ensure the cache_dir exists otherwise log initialisation will fail
        Util.mkdir_p(self.cache_dir)
        self.log_file = os.path.join(self.cache_dir, "ensime.log")
        if self.logger is None:
            self.logger = self.create_logger(debug, self.log_file)

        return True

    def is_running(self):
        """Tells if the ensime server is up and client is connected to it."""
        return self.client is not None and self.client.running

    def is_connected(self):
        return self.client is not None and self.client.connected

    def status_message(self, msg):
        sublime.set_timeout(bind(sublime.status_message, msg), 0)

    def error_message(self, msg):
        sublime.set_timeout(bind(sublime.error_message, msg), 0)

    def shutdown(self):
        self.client.teardown()
        self.valid = False
        self.notes_storage = None
        self.editor = None
        self.client = None
        self.logger = None
        # reverting changings to user preferences
        s = sublime.load_settings("Preferences.sublime-settings")
        s.set("auto_complete", self.previous_auto_complete)
        s.set("show_definitions", self.previous_show_definitions)
        sublime.save_settings("Preferences.sublime-settings")

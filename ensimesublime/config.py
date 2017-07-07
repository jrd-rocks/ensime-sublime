# coding: utf-8

import collections
import os

import sexpdata

from util import Util

LOG_FORMAT = '%(levelname)-8s <%(asctime)s> (%(filename)s:%(lineno)d) - %(message)s'

gconfig = {
    "ensime_server": "ws://127.0.0.1:{}/{}",
    "localhost": "http://127.0.0.1:{}/{}",
}

# Messages for user feedback, possible l10n fodder. Please keep alphabetized.
feedback = {
    "analyzer_ready": "Analyzer is ready",
    "failed_refactoring": "The refactoring could not be applied (more info at logs)",
    "full_types_enabled_off": "Qualified type display disabled",
    "full_types_enabled_on": "Qualified type display enabled",
    "handler_not_implemented":
        "The feature {} is not supported by the current Ensime server version {}",
    "indexer_ready": "Indexer is ready",
    "invalid_java": "Java not found or not executable, verify :java-home in your .ensime config",
    "manual_doc": "Go to {}",
    "missing_debug_class": "You must specify a class to debug",
    "notify_break": "Execution paused at breakpoint line {} in {}",
    "package_inspect_current": "Using currently focused package...",
    "prompt_server_install":
        "Please run :EnInstall to install the ENSIME server for Scala {scala_version}",
    "spawned_browser": "Opened tab {}",
    "start_message": "Server has been started...",
    "symbol_search_symbol_required": "Must provide symbols to search for!",
    "typechecking": "Typechecking...",
    "unknown_symbol": "Symbol not found",
}


# class EnsimeProjectId(object):
#     def __init__(self, project, config):
#         self.project = project
#         self.config = config

#     def __hash__(self):
#         return hash(self.project) ^ hash(self.config)

#     def __eq__(self, that):
#         return self.project == that.project and self.config == that.config

#     def __repr__(self):
#         return ("EnsimeProjectId({project}, {config})"
#                 .format(project=self.project, config=self.config))


class ProjectConfig(collections.Mapping):
    """A dict-like immutable representation of an ENSIME project configuration.

    Args:
        filepath (str): Path of an ``.ensime`` file to parse.
    """

    def __init__(self, filepath):
        self._filepath = os.path.realpath(filepath)
        self.__data = self.parse(filepath)

    # Provide the Mapping protocol requirements

    def __getitem__(self, key):
        return self.__data[key]

    def __iter__(self):
        return iter(self.__data)

    def __len__(self):
        return len(self.__data)

    def __repr__(self):
        return "{name}({path!r})".format(
            name=self.__class__.__name__,
            path=self.filepath
        )

    @property
    def filepath(self):
        """str: The canonical path of the represented config file."""
        return self._filepath

    @staticmethod
    def parse(path):
        """Parse an ``.ensime`` config file from S-expressions.

        Args:
            path (str): Path of an ``.ensime`` file to parse.

        Returns:
            dict: Configuration values with string keys.
        """

        def paired(iterable):
            """s -> (s0, s1), (s2, s3), (s4, s5), ..."""
            cursor = iter(iterable)
            return zip(cursor, cursor)

        def unwrap_if_sexp_symbol(datum):
            """Convert Symbol(':key') to ':key' (Symbol isn't hashable for dict keys).
            """
            return datum.value() if isinstance(datum, sexpdata.Symbol) else datum

        def sexp2dict(sexps):
            """Transforms a nested list structure from sexpdata to dict."""
            newdict = {}

            # Turn flat list into associative pairs
            for key, value in paired(sexps):
                key = str(unwrap_if_sexp_symbol(key)).lstrip(':')

                # Recursively transform nested lists
                if isinstance(value, list) and value and isinstance(value[0], list):
                    newdict[key] = [sexp2dict(val) for val in value]
                elif isinstance(value, list) and value and isinstance(value[0], sexpdata.Symbol):
                    newdict[key] = sexp2dict(value)
                else:
                    newdict[key] = value

            return newdict

        conf = sexpdata.loads(Util.read_file(path))
        return sexp2dict(conf)

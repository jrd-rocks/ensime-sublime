import os
from contextlib import contextmanager
from pprint import pformat


@contextmanager
def catch(exception, handler=lambda e: None):
    """If exception runs handler."""
    try:
        yield
    except exception as e:
        handler(str(e))


class Util(object):
    @staticmethod
    def read_file(path):
        with open(path, "r") as f:
            result = f.read()
        return result

    @staticmethod
    def write_file(path, contents):
        with open(path, "w") as f:
            result = f.write(contents)
        return result

    @staticmethod
    def mkdir_p(path):
        if not os.path.exists(path):
            os.makedirs(path)

    @staticmethod
    def is_scala(path):
        return path.endswith(".scala")

    @staticmethod
    def is_java(path):
        return path.endswith(".java")


class Pretty(object):
    """Wrapper to pretty-format object's string representation.

    Reduces boilerplate for logging statements where we don't want to eagerly
    :func:`pprint.pformat` when the logging level isn't enabled.
    """
    def __init__(self, data):
        self._data = data

    def __str__(self):
        return '\n' + pformat(self._data)

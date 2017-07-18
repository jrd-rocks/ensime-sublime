import os
import sys


# pytest expects the project modules to be importable from whereever you run
# it, preferring that you do `pip install --editable .` -- we don't want to be
# a distributable Python package so this is easier than maintaining a useless
# setup.py.
parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent)
sys.path += [os.path.join(parent, "dependencies"),
             os.path.join(parent, "ensimesublime")]

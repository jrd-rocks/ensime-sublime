import mock
from py import path
from pytest import raises

from dotensime import load
from config import ProjectConfig
from errors import DotEnsimeNotFound

resources = path.local(__file__).dirpath() / 'resources'


def test_loads_dot_ensime():
    attrs = {'folders.return_value': [str(resources / 'mockproject')]}
    window = mock.NonCallableMock(name='mockwindow', **attrs)
    config = load(window)
    assert type(config) == ProjectConfig


def test_raises_DotEnsimeNotFound():
    attrs = {'folders.return_value': [str(resources / 'mockempty')]}
    window = mock.NonCallableMock(name='mockwindow', **attrs)
    with raises(DotEnsimeNotFound):
        config = load(window)

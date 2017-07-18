# coding: utf-8

from py import path
from pytest import raises
import sexpdata

from config import ProjectConfig

confpath = path.local(__file__).dirpath() / 'resources' / 'test.conf'
config = ProjectConfig(confpath.strpath)


def test_parses_dot_ensime():
    assert config.get('scala-version') == '2.11.8'
    assert config.get('list') == ["a", "b", "c", "d"]
    assert len(config['nest']) == 2
    assert config['nest'][0]['id'] == {'config': 'conf1', 'name': 'nested1'}
    assert config['nest'][0]['targets'] == ['abc', 'xyz']


def test_is_immutable():
    with raises(TypeError) as excinfo:
        config['scala-version'] = 'bogus'
    assert 'does not support item assignment' in str(excinfo.value)


def test_is_dict_like():
    assert set(config.keys()) == set(['name', 'scala-version', 'list', 'nest'])
    assert len(config) == 4


def test_fails_when_given_invalid_config():
    badconf = path.local(__file__).dirpath() / 'resources' / 'broken.conf'
    with raises(sexpdata.ExpectClosingBracket):
        ProjectConfig(badconf.strpath)

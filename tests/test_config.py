# coding: utf-8

from py import path
from pytest import raises

from ensimesublime.config import ProjectConfig
from ensimesublime.errors import BadEnsimeConfig

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


def test_fails_when_given_invalid_config():
    badconf = path.local(__file__).dirpath() / 'resources' / 'broken.conf'
    with raises(BadEnsimeConfig):
        ProjectConfig(badconf.strpath)

# coding: utf-8

import pytest
from mock import patch
from py import path

from config import ProjectConfig
from errors import LaunchError
from launcher import DotEnsimeLauncher

CONFROOT = path.local(__file__).dirpath() / 'resources'


class TestDotEnsimeStrategy:
    @pytest.fixture
    def strategy(self):
        return DotEnsimeLauncher(config('test-server-jars.conf'))

    def test_adds_server_jars_to_classpath(self, strategy):
        server_jars = strategy.config['ensime-server-jars']
        assert all([jar in strategy.classpath for jar in server_jars])

    def test_isinstalled_if_jars_present(self, strategy):
        assert not strategy.isinstalled()
        # Stub the existence of the server+compiler jars
        with patch('os.path.exists', return_value=True):
            assert strategy.isinstalled()

    def test_launch_constructs_classpath(self, strategy):
        with patch.object(strategy, '_start_process', autospec=True) as start:
            with patch.object(strategy, 'isinstalled', return_value=True):
                strategy.launch()

        assert start.call_count == 1
        args, _kwargs = start.call_args
        classpath = args[0]
        assert classpath == strategy.classpath

    def test_launch_raises_when_not_installed(self, strategy):
        assert not strategy.isinstalled()
        with pytest.raises(LaunchError) as excinfo:
            strategy.launch()
        assert 'Some jars reported by .ensime do not exist' in str(excinfo.value)


# -----------------------------------------------------------------------
# -                               Helpers                               -
# -----------------------------------------------------------------------

def config(conffile):
    return ProjectConfig(CONFROOT.join(conffile).strpath)


def create_stub_assembly_jar(indir, projectconfig):
    """Touches assembly jar file path in indir and returns the path."""
    scala_minor = projectconfig['scala-version'][:4]
    name = 'ensime_{}-assembly.jar'.format(scala_minor)
    return path.local(indir).ensure(name).realpath

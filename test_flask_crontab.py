import pytest
from unittest import mock
from functools import partial

from flask import Flask, current_app
import flask_crontab


@pytest.fixture()
def crontab():
    app = Flask(__name__)
    return flask_crontab.Crontab(app)


@pytest.fixture()
def source():
    return []


@pytest.fixture()
def _crontab(crontab, monkeypatch, source):
    def write(self):
        source[:] = self.crontab_lines

    def read(self):
        self.crontab_lines[:] = source

    with crontab.app.app_context():
        flask_crontab._Crontab.read = read
        flask_crontab._Crontab.write = write
        rv = flask_crontab._Crontab()
        monkeypatch.setattr(flask_crontab, "_Crontab", mock.Mock(return_value=rv))
        yield rv


@pytest.fixture()
def invoke(crontab):
    runner = crontab.app.test_cli_runner()
    return partial(runner.invoke, cli=flask_crontab.crontab_cli)


def test_add_jobs(crontab, _crontab, invoke):
    @crontab.job()
    def foo():
        pass

    result = invoke(args=["add"])
    assert result.exit_code == 0
    assert (
        "Adding cronjob: 98fa712b876a5ec6f63cff664b748da3 -> test_flask_crontab:foo"
        in result.output
    )
    assert "* * * * *" in _crontab.crontab_lines[0]


def test_remove_jobs(crontab, _crontab, invoke, source):
    source[:] = ["* * * * * echo hello", "*/5 * * * mon-fri echo foobar"]

    @crontab.job()
    def foo():
        pass

    result = invoke(args=["add"])
    assert len(_crontab.crontab_lines) == 3
    result = invoke(args=["remove"])
    assert result.exit_code == 0
    assert (
        "Removing cronjob: 98fa712b876a5ec6f63cff664b748da3 -> test_flask_crontab:foo"
        in result.output
    )
    assert len(_crontab.crontab_lines) == 2


def test_show_jobs(crontab, _crontab, invoke):
    @crontab.job()
    def foo():
        pass

    @crontab.job()
    def bar():
        pass

    invoke(args=["add"])
    result = invoke(args=["show"])
    assert result.exit_code == 0
    assert "98fa712b876a5ec6f63cff664b748da3 -> test_flask_crontab:foo" in result.output
    assert "f27593c4417a660d5bcaf0d498179e67 -> test_flask_crontab:bar" in result.output


def test_run_jobs(crontab, _crontab, invoke):
    foo = mock.Mock()
    foo.__name__ = "foo"
    foo.__module__ = __name__

    crontab.job()(foo)
    crontab.job(args=("hello",), kwargs={"name": "John"})(foo)

    invoke(args=["add"])
    result = invoke(args=["run", "98fa712b876a5ec6f63cff664b748da3"])
    assert result.exit_code == 0
    foo.assert_called()
    result = invoke(args=["run", "625b3192eb860a8a0bb0a43656cedf98"])
    assert result.exit_code == 0
    foo.assert_called_with("hello", name="John")


def test_run_with_appcontext(crontab, _crontab, invoke):
    @crontab.job()
    def check_config():
        assert current_app.config["CRONTAB_EXECUTABLE"] == "/usr/bin/crontab"
        assert not current_app.config["CRONTAB_LOCK_JOBS"]

    result = invoke(args=["run", "c1ad6548c98a4fda072c8b7bab20b189"])
    assert result.exit_code == 0

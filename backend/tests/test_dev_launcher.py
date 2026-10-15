"""Launcher lifecycle checks; no model calls, database, or project servers."""
import importlib.util
from pathlib import Path
import signal

import pytest


@pytest.fixture
def launcher():
    path = Path(__file__).resolve().parents[2] / "scripts/dev.py"
    spec = importlib.util.spec_from_file_location("local_dev_launcher", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Child:
    pid = 12345

    def __init__(self, code=None):
        self.returncode = code

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        self.returncode = 143 if self.returncode is None else self.returncode
        return self.returncode


def test_terminated_group_permission_race_requires_confirmed_group_exit(launcher, monkeypatch):
    calls = []
    def killpg(pid, signum):
        calls.append(signum)
        if signum:
            raise PermissionError("synthetic exit race")
        raise ProcessLookupError("group is gone")
    monkeypatch.setattr(launcher.os, "killpg", killpg)
    launcher.signal_process_group(Child(0), signal.SIGTERM)
    assert calls == [signal.SIGTERM, 0]


@pytest.mark.parametrize("child_code,group_exists", [(None, True), (0, True)])
def test_permission_error_for_live_or_unverified_group_is_not_hidden(launcher, monkeypatch, child_code, group_exists):
    def killpg(pid, signum):
        raise PermissionError("synthetic live group permission failure")
    monkeypatch.setattr(launcher.os, "killpg", killpg)
    with pytest.raises(PermissionError):
        launcher.signal_process_group(Child(child_code), signal.SIGTERM)


def test_repeated_operator_signals_cleanup_once_and_return_success(launcher, monkeypatch):
    handlers, stopped = {}, []
    children = [Child(), Child()]
    monkeypatch.setattr(launcher.signal, "signal", lambda sig, handler: handlers.setdefault(sig, handler))
    monkeypatch.setattr(launcher.subprocess, "Popen", lambda *args, **kwargs: children.pop(0))
    def request_stop(_seconds):
        handlers[signal.SIGINT](signal.SIGINT, None)
        handlers[signal.SIGTERM](signal.SIGTERM, None)
    monkeypatch.setattr(launcher.time, "sleep", request_stop)
    monkeypatch.setattr(launcher.os, "killpg", lambda pid, signum: stopped.append(signum))
    assert launcher.main() == 0
    assert stopped == [signal.SIGTERM, signal.SIGTERM]


def test_independent_startup_failure_remains_nonzero_and_stops_sibling(launcher, monkeypatch):
    children = [Child(), Child(1)]
    stopped = []
    monkeypatch.setattr(launcher.signal, "signal", lambda *_: signal.SIG_DFL)
    monkeypatch.setattr(launcher.subprocess, "Popen", lambda *args, **kwargs: children.pop(0))
    monkeypatch.setattr(launcher.os, "killpg", lambda pid, signum: stopped.append(signum))
    assert launcher.main() == 1
    assert stopped == [signal.SIGTERM, signal.SIGTERM]

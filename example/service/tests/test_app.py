import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app  # noqa: E402

NOW = 1_000_000.0


class FakeNotifier:
    def __init__(self, delivered=True):
        self.delivered = delivered
        self.sent = []

    def send(self, message):
        self.sent.append(message)
        return {"delivered": self.delivered}


def event(age_s=0, version=2, payload=None):
    return {"created": NOW - age_s, "version": version, "payload": payload or {"k": 1}}


def test_fresh_event_is_acted_on(tmp_path):
    result = app.run_cycle(lambda: event(), FakeNotifier(), tmp_path / "HALT.flag", now=NOW)
    assert result["acted"] is True


def test_event_36_hours_old_holds(tmp_path):
    result = app.run_cycle(
        lambda: event(age_s=36 * 3600), FakeNotifier(), tmp_path / "HALT.flag", now=NOW
    )
    assert result == {"acted": False, "reason": "hold", "paged": True}


def test_halt_flag_blocks_the_cycle(tmp_path):
    flag = tmp_path / "HALT.flag"
    flag.touch()
    result = app.run_cycle(lambda: event(), FakeNotifier(), flag, now=NOW)
    assert result["reason"] == "halted"


def test_hold_pages_the_human(tmp_path, monkeypatch):
    monkeypatch.setattr(app, "page", lambda notifier, message: True)
    result = app.run_cycle(lambda: None, FakeNotifier(), tmp_path / "HALT.flag", now=NOW)
    assert result["paged"] is True

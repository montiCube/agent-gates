"""A toy service for the agent-gates example.

Each cycle it reads one configuration event and either acts on it or holds.
It follows a reduced form of ledger entry LL-002: an event is acted on only
if it is accepted; a failed, absent or refused read holds. When it holds, it
pages a human.
"""

import time
from pathlib import Path

MAX_EVENT_AGE_S = 36 * 3600  # LL-002: 36 hours old or more is refused
EXPECTED_VERSION = 2


def accept(event, now):
    """Return True if the event may be acted on. LL-002."""
    if not event or not event.get("payload"):
        return False
    if event.get("version") != EXPECTED_VERSION:
        return False
    return now - event["created"] < MAX_EVENT_AGE_S


def page(notifier, message):
    """Send a page. Return True only if the notifier delivered it."""
    result = notifier.send(message)
    return result.get("delivered") is True  # LL-003


def run_cycle(read_event, notifier, halt_flag, now=None):
    """Run one cycle and return what it did, for the record."""
    now = time.time() if now is None else now
    if Path(halt_flag).exists():
        return {"acted": False, "reason": "halted", "paged": False}
    try:
        event = read_event()
    except Exception:
        event = None
    if not accept(event, now):
        paged = page(notifier, "holding: no accepted configuration event")
        return {"acted": False, "reason": "hold", "paged": paged}
    return {"acted": True, "reason": "accepted", "paged": False}

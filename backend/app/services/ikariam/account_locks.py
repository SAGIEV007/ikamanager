"""Per-account request serialization.

A normal player never fires two actions at the same instant, and crucially never
sends other requests while a piracy mission/captcha is being resolved. To mimic
that (and avoid tripping anti-bot heuristics), every game action for a given
account is serialized behind a single lock: while one action is in flight
(including the whole captcha-solving loop), any other action for that account
waits its turn.
"""

import asyncio

_LOCKS: dict[int, asyncio.Lock] = {}


def get_lock(account_id: int) -> asyncio.Lock:
    """Return the shared lock for an account, creating it on first use."""
    lock = _LOCKS.get(account_id)
    if lock is None:
        lock = asyncio.Lock()
        _LOCKS[account_id] = lock
    return lock


def is_busy(account_id: int) -> bool:
    """True if an action is currently in flight for this account."""
    lock = _LOCKS.get(account_id)
    return lock is not None and lock.locked()

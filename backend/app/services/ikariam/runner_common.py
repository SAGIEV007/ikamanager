"""Shared helpers for the background runners (donations and building upgrades).

Keeping these in one place ensures every automatic loop enforces the same
behaviour: operation-hours windows, per-account proxy resolution and
human-like timing jitter (so requests aren't sent in robotic bursts).
"""

import random
from datetime import datetime
from typing import Optional

from sqlalchemy import select

from app.models.account import IkariamAccount
from app.models.proxy import Proxy


def seconds_until_window(
    start_hour: int,
    end_hour: int,
    now: Optional[datetime] = None,
) -> int:
    """Seconds to wait until inside the operation window; 0 if already inside.

    Supports windows that wrap past midnight (e.g. start=22, end=6) and treats
    ``start == end`` as "no restriction" (24h operation).
    """
    now = now or datetime.now()
    if start_hour == end_hour:
        return 0  # no restriction (24h)
    h = now.hour + now.minute / 60 + now.second / 3600
    if start_hour < end_hour:
        inside = start_hour <= h < end_hour
    else:  # wraps midnight
        inside = h >= start_hour or h < end_hour
    if inside:
        return 0
    target = now.replace(hour=int(start_hour) % 24, minute=0, second=0, microsecond=0)
    delta = (target - now).total_seconds()
    if delta <= 0:
        delta += 24 * 3600
    return int(delta)


async def resolve_proxy_url(db, account: IkariamAccount) -> Optional[str]:
    """Return the configured proxy URL for an account, if any."""
    if not account.proxy_id:
        return None
    result = await db.execute(select(Proxy).where(Proxy.id == account.proxy_id))
    proxy = result.scalar_one_or_none()
    return proxy.url if proxy else None


def human_wait(base_wait: int, extra_wait_max: int) -> int:
    """Human-like wait between actions.

    - the base interval (mission duration or configured interval)
    - a uniform random extra (0..extra_wait_max)
    - a small always-on jitter so intervals are never identical/robotic
    - a ~12% chance of a longer "coffee break" (2-8 min) to look human
    """
    wait_s = base_wait + random.randint(0, max(0, extra_wait_max))
    wait_s += random.randint(5, 45)
    if random.random() < 0.12:
        wait_s += random.randint(120, 480)
    return wait_s

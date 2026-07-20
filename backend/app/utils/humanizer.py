"""Utilities to simulate human-like behavior."""

import asyncio
import random


async def random_delay(min_seconds: float = 2.0, max_seconds: float = 6.0):
    """Wait a random amount of time to simulate human behavior."""
    delay = random.uniform(min_seconds, max_seconds)
    await asyncio.sleep(delay)


def random_typing_delay() -> float:
    """Simulate typing speed variation."""
    return random.uniform(0.05, 0.15)


def jitter(base_seconds: float, factor: float = 0.3) -> float:
    """Add random jitter to a base delay."""
    jitter_amount = base_seconds * factor
    return base_seconds + random.uniform(-jitter_amount, jitter_amount)


def should_take_break(action_count: int, threshold: int = 15) -> bool:
    """Determine if a longer break should be taken after many actions."""
    if action_count >= threshold:
        return random.random() < 0.7  # 70% chance of break
    return False


async def human_break(min_seconds: float = 30.0, max_seconds: float = 120.0):
    """Take a longer break to simulate human behavior."""
    delay = random.uniform(min_seconds, max_seconds)
    await asyncio.sleep(delay)

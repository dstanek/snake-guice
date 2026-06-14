"""A small seam around "what time is it" so task creation is testable."""

from datetime import datetime, timezone


class Clock:
    def now(self) -> datetime:
        raise NotImplementedError


class SystemClock(Clock):
    def now(self) -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)

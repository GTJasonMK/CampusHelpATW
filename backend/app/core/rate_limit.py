from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock

from app.core.errors import AppError


@dataclass
class LimitRule:
    key: str
    max_count: int
    window_seconds: int


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[datetime]] = defaultdict(deque)
        self._lock = Lock()

    def hit(self, user_id: int, rule: LimitRule) -> None:
        if rule.max_count <= 0 or rule.window_seconds <= 0:
            return

        now = datetime.now(timezone.utc)
        window_start = now - timedelta(seconds=rule.window_seconds)
        slot = f"{rule.key}:{int(user_id)}"

        with self._lock:
            q = self._hits[slot]
            while q and q[0] < window_start:
                q.popleft()
            if len(q) >= rule.max_count:
                raise AppError(
                    code=4011,
                    message=(
                        f"rate limit exceeded for {rule.key}: "
                        f"{rule.max_count} requests / {rule.window_seconds}s"
                    ),
                    http_status=429,
                )
            q.append(now)


rate_limiter = InMemoryRateLimiter()

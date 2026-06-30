"""Global asyncio lock — only one Playwright analysis at a time."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass


@dataclass
class ActiveAnalysis:
    lead_id: int
    url: str


class AnalysisLock:
    """Serializes Playwright runs across all API workers in one process."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._active: ActiveAnalysis | None = None

    @property
    def is_busy(self) -> bool:
        return self._lock.locked()

    @property
    def active(self) -> ActiveAnalysis | None:
        return self._active

    async def acquire(self, lead_id: int, url: str) -> None:
        if self._lock.locked():
            raise RuntimeError("Another website analysis is already running")
        await self._lock.acquire()
        self._active = ActiveAnalysis(lead_id=lead_id, url=url)

    def release(self) -> None:
        self._active = None
        if self._lock.locked():
            self._lock.release()


analysis_lock = AnalysisLock()
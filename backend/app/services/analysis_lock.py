"""Lock global asyncio — solo UN análisis de Playwright a la vez.

Playwright abre un navegador Chromium completo: correr varios en paralelo en
una máquina modesta agota RAM/CPU. Este lock serializa los análisis y expone
quién lo tiene (lead + URL) para que la UI muestre "ocupado con…".
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass


@dataclass
class ActiveAnalysis:
    """Qué análisis tiene el lock ahora mismo."""
    lead_id: int   # lead que se está analizando
    url: str       # URL que se está auditando


class AnalysisLock:
    """Serializa las corridas de Playwright dentro del proceso de la API."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()                 # el candado real
        self._active: ActiveAnalysis | None = None  # metadatos del análisis en curso

    @property
    def is_busy(self) -> bool:
        # ¿Hay un análisis corriendo? (lo consulta /website-research/status)
        return self._lock.locked()

    @property
    def active(self) -> ActiveAnalysis | None:
        # Detalles del análisis activo (o None si está libre)
        return self._active

    async def acquire(self, lead_id: int, url: str) -> None:
        # Rechaza en vez de encolar: el cliente recibe 409 y reintenta después
        if self._lock.locked():
            raise RuntimeError("Another website analysis is already running")
        await self._lock.acquire()
        self._active = ActiveAnalysis(lead_id=lead_id, url=url)

    def release(self) -> None:
        # Limpia los metadatos y suelta el candado (seguro llamarlo dos veces)
        self._active = None
        if self._lock.locked():
            self._lock.release()


# Instancia única compartida por todos los endpoints
analysis_lock = AnalysisLock()

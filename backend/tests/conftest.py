"""Shared pytest fixtures with isolated SQLite databases."""

from __future__ import annotations

import importlib
import sys
from collections.abc import Generator
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture()
def isolated_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator:
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")

    import backend.app.config as config
    import backend.app.database as database

    importlib.reload(config)
    importlib.reload(database)

    import scripts.process_leads as process_leads

    importlib.reload(process_leads)

    yield database

    database.engine.dispose()
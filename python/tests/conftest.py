from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from .helpers import wait_for_save_in_db


class KoloStorage:
    data_directory = Path(os.environ.get("KOLO_PATH", ".")) / ".kolo"
    db_path = data_directory / "db.sqlite3"


@pytest.fixture
def kolo_storage():
    storage = KoloStorage()

    yield storage

    wait_for_save_in_db()
    try:
        shutil.rmtree(storage.data_directory)
    except FileNotFoundError:
        pass


@pytest.fixture(autouse=True, scope="session")
def prime_import_cache():
    """Ensure some modules are imported before the test starts to avoid extra frames"""
    try:
        import tests.urls
    except ImportError:  # pragma: no cover
        pass

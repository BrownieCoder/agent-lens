import importlib.util
from pathlib import Path
import sqlite3

import pytest


def test_snapshot_restores_rows_and_refuses_overwrite(tmp_path):
    script = Path(__file__).resolve().parents[2] / "scripts/database_snapshot.py"
    spec = importlib.util.spec_from_file_location("database_snapshot", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source = tmp_path / "source.sqlite"
    with sqlite3.connect(source) as db:
        db.execute("CREATE TABLE evidence (id INTEGER PRIMARY KEY, label TEXT)")
        db.execute("INSERT INTO evidence VALUES (1, 'synthetic')")
    backup = tmp_path / "backup.sqlite"
    restored = tmp_path / "restore.sqlite"
    module.snapshot(source, backup)
    module.snapshot(backup, restored)
    with sqlite3.connect(restored) as db:
        assert db.execute("SELECT * FROM evidence").fetchall() == [(1, "synthetic")]
    with pytest.raises(ValueError):
        module.snapshot(source, restored)
    with pytest.raises(FileNotFoundError):
        module.snapshot(tmp_path / "absent.sqlite", tmp_path / "unused.sqlite")
    assert not (tmp_path / "unused.sqlite").exists()

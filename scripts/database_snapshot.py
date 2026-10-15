"""Consistent SQLite backup/restore to a NEW path. Never overwrite a database."""
import argparse
import os
from pathlib import Path
import sqlite3


def snapshot(source: Path, destination: Path) -> None:
    source = source.resolve(strict=True)
    destination = destination.resolve()
    if source == destination or destination.exists():
        raise ValueError("Destination must be a new path; existing files are never overwritten")
    source_db = sqlite3.connect(f"{source.as_uri()}?mode=ro", uri=True, timeout=10)
    try:
        if source_db.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise ValueError("Source failed SQLite integrity_check; preserve it for investigation")
        if source_db.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("Source has invalid foreign keys; preserve it for investigation")
        fd = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        target_db = sqlite3.connect(destination)
        try:
            source_db.backup(target_db)
            if target_db.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                raise ValueError("Snapshot integrity check failed; do not use the destination")
            if target_db.execute("PRAGMA foreign_key_check").fetchall():
                raise ValueError("Snapshot foreign key check failed; do not use the destination")
        finally:
            target_db.close()
    finally:
        source_db.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("backup", "restore"))
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    try:
        snapshot(args.source, args.destination)
    except (OSError, ValueError, sqlite3.Error) as error:
        parser.exit(1, f"Snapshot failed ({type(error).__name__}). Keep the source unchanged; use a new destination after checking paths, integrity and permissions.\n")
    print(f"{args.action.capitalize()} complete; integrity and foreign keys verified. Source unchanged.")


if __name__ == "__main__":
    main()

"""Run the two loopback-only services and stop their process groups together."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    children: list[subprocess.Popen] = []

    def stop(_signum=None, _frame=None):
        for child in children:
            try:
                os.killpg(child.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        children.append(subprocess.Popen(
            [str(ROOT / "backend/.venv/bin/uvicorn"), "app.main:app", "--host", "127.0.0.1", "--port", "8000", "--workers", "1"],
            cwd=ROOT / "backend", start_new_session=True,
        ))
        children.append(subprocess.Popen(
            ["npm", "run", "dev", "--", "--host", "127.0.0.1", "--strictPort"],
            cwd=ROOT / "frontend", start_new_session=True,
        ))
        while all(child.poll() is None for child in children):
            time.sleep(0.2)
        return next((child.returncode for child in children if child.returncode not in (None, 0, -15, -2)), 0)
    except OSError as error:
        print(f"Cannot start local services: {error}. Run make setup first.", file=sys.stderr)
        return 1
    finally:
        stop()
        for child in children:
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                child.wait()


if __name__ == "__main__":
    raise SystemExit(main())

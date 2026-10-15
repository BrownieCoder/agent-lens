"""Run the two loopback-only services and stop their process groups together."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def signal_process_group(child: subprocess.Popen, signum: int) -> None:
    try:
        os.killpg(child.pid, signum)
    except ProcessLookupError:
        return  # The entire group has already exited.
    except PermissionError:
        # A live group permission failure is a real cleanup error. Only ignore
        # an exit race when both the child and a fresh group probe confirm exit.
        if child.poll() is not None:
            try:
                os.killpg(child.pid, 0)
            except ProcessLookupError:
                return
        raise


def stop_children(children: list[subprocess.Popen]) -> bool:
    succeeded = True
    for child in children:
        try:
            signal_process_group(child, signal.SIGTERM)
        except OSError as error:
            print(f"Cannot stop local service group {child.pid}: {error}", file=sys.stderr)
            succeeded = False
    for child in children:
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                signal_process_group(child, signal.SIGKILL)
                child.wait(timeout=5)
            except (OSError, subprocess.TimeoutExpired) as error:
                print(f"Cannot finish stopping local service group {child.pid}: {error}", file=sys.stderr)
                succeeded = False
    return succeeded


def main() -> int:
    children: list[subprocess.Popen] = []
    shutdown_requested = False

    def request_shutdown(_signum, _frame):
        nonlocal shutdown_requested
        # Signal handlers only record intent. Cleanup runs once in normal control
        # flow, so a second signal cannot reenter kill/wait on an exited group.
        shutdown_requested = True

    previous_handlers = {
        sig: signal.signal(sig, request_shutdown) for sig in (signal.SIGTERM, signal.SIGINT)
    }
    exit_code = 0
    try:
        children.append(subprocess.Popen(
            [str(ROOT / "backend/.venv/bin/uvicorn"), "app.main:app", "--host", "127.0.0.1", "--port", "8000", "--workers", "1"],
            cwd=ROOT / "backend", start_new_session=True,
        ))
        if not shutdown_requested:
            children.append(subprocess.Popen(
                ["npm", "run", "dev", "--", "--host", "127.0.0.1", "--strictPort"],
                cwd=ROOT / "frontend", start_new_session=True,
            ))
        while not shutdown_requested and all(child.poll() is None for child in children):
            time.sleep(0.2)
        if not shutdown_requested:
            # An independently failed service remains a failure. User-requested
            # shutdown instead succeeds even when npm reports shell status 143.
            exit_code = next((child.returncode for child in children if child.returncode not in (None, 0)), 0)
            if exit_code < 0:
                exit_code = 128 - exit_code
    except OSError as error:
        print(f"Cannot start local services: {error}. Run make setup first.", file=sys.stderr)
        exit_code = 1
    finally:
        if not stop_children(children):
            exit_code = 1
        for sig, previous in previous_handlers.items():
            signal.signal(sig, previous)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())

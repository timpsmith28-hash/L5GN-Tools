"""The window launcher -- COWORK_BRIEF_unified_app.md Task 5.

Starts `run.py app` (the single entry point, DECISIONS 0035) as a
subprocess bound to an EPHEMERAL loopback port, waits for it to answer
`/api/health`, then opens a `pywebview` window pointed at it. Closing the
window shuts the server down -- no orphan uvicorn.

**A subprocess, not an in-process ASGI thread.** `run.py app`'s own
preflight (vault/estate/curator, the estate-wall bind check, the status
prints) already exists, is already tested, and already prints exactly
what an operator needs to debug a degraded surface. Re-implementing that
preflight inline here to save one process would duplicate ~150 lines of
already-careful logic for no benefit, and a subprocess you can see in
`ps` / Task Manager is easier to reason about than an ASGI server quietly
running on a thread inside a GUI process (INTENT §3, "could I debug this
at 2am") -- the same instinct `run.py serve` already applies by shelling
out to `datasette` rather than embedding it.

**Ephemeral, not a fixed port.** A fixed port is a collision waiting for
the day two things want it, and this launcher exists to be clicked from a
shortcut -- an action with no memory of whether it was already clicked
once today.

**A second instance must refuse or focus the first.** This one refuses:
a lock file (`data/app.lock`) names the port and pid of a running
instance. A second launch checks whether that port still answers
`/api/health` -- not just whether the pid is alive, which is a weaker and
less portable check (`os.kill(pid, 0)` does not mean the same thing on
Windows as POSIX) -- and if it does, refuses to start a second server
against the same vault (INTENT §5: one writer) rather than attempting to
focus another process's OS window, which has no simple cross-platform
answer. A stale lock (the process crashed without cleaning up) is
harmless: the health check fails, and this launcher proceeds and
overwrites it.

**The window failing to open is a first-class, exercised path, not a
theoretical one.** No GTK or Qt backend is the common case on a fresh
machine, and it is literally the case in the sandbox this file was
written and tested in: `import webview; webview.create_window(...);
webview.start()` was run by hand here and raised `WebViewException` with
"You must have either QT or GTK with Python extensions installed". The
fallback -- print the loopback URL, leave the server running, wait on it
-- was exercised by hand too, not assumed. Never a silent exit.
"""
from __future__ import annotations

import json
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from l5gntools.common import DATA_DIR, TOOLKIT_ROOT

LOCK_PATH: Path = DATA_DIR / "app.lock"
_RUN_PY: Path = TOOLKIT_ROOT / "run.py"

HEALTH_TIMEOUT_S = 20
HEALTH_POLL_INTERVAL_S = 0.25
LOCK_CHECK_TIMEOUT_S = 1.5


def _health_ok(port: int, timeout_s: float) -> bool:
    """True iff something answers `/api/health` with 200 on this port,
    right now. Used both to detect an already-running instance and to
    wait for the one this launcher just started."""
    url = f"http://127.0.0.1:{port}/api/health"
    try:
        with urllib.request.urlopen(url, timeout=timeout_s) as resp:
            return resp.status == 200
    except (urllib.error.URLError, OSError, ValueError):
        return False


def _wait_for_health(port: int, timeout_s: float = HEALTH_TIMEOUT_S) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if _health_ok(port, timeout_s=1):
            return True
        time.sleep(HEALTH_POLL_INTERVAL_S)
    return False


def _ephemeral_port() -> int:
    """Ask the OS for a free loopback port and hand it back closed --
    there is a narrow race between closing this socket and the subprocess
    binding the same number, same as every "ask the OS for a free port"
    recipe; accepted here for the same reason it usually is: the window
    this launcher runs in is short, local-only, and the failure mode
    (the subprocess fails to bind and `_wait_for_health` times out) is
    visible and reported, never silent."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
    finally:
        s.close()


def _already_running() -> dict | None:
    """The lock file's contents, IFF the port it names is actually still
    answering /api/health right now. A lock file whose port has gone
    quiet (a crash, a kill -9) is stale, not evidence of a running
    instance -- reported as absent so this launcher proceeds and
    overwrites it, rather than refusing forever because of a leftover
    file."""
    if not LOCK_PATH.is_file():
        return None
    try:
        info = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
    port = info.get("port")
    if not isinstance(port, int):
        return None
    if _health_ok(port, timeout_s=LOCK_CHECK_TIMEOUT_S):
        return info
    return None


def _open_window(url: str) -> bool:
    """True iff a window actually opened and was closed by the user (the
    normal, successful path). False means "no usable window backend" --
    the caller's job, not this function's, to decide what to do about it.

    `webview.start()` is blocking: it runs the GUI event loop until the
    window closes, which is what makes "closing the window shuts the
    server down" true by construction -- the caller's cleanup runs the
    moment this function returns, whichever branch it returned from.
    """
    try:
        import webview
    except ImportError:
        return False
    try:
        webview.create_window("Chronicler — Command Deck", url)
        webview.start()
        return True
    except Exception as exc:  # noqa: BLE001 -- any backend failure means "no window"
        print(f"app: window failed to open ({type(exc).__name__}: {exc}).",
              file=sys.stderr)
        return False


class _Terminated(SystemExit):
    """Raised from the SIGTERM handler so the `finally` in `run()` still
    fires. Python's default SIGTERM disposition kills the process without
    running cleanup -- and SIGTERM, not SIGINT, is what `timeout`, `kill`,
    a systemd stop, and Windows Task Manager's "End Task" all send by
    default. Without this, the lock file and the child `run.py app`
    survive the launcher (a stale lock is self-healing -- the next launch's
    `_already_running()` finds a dead port and overwrites it -- but there
    is no reason to leave the mess when catching the signal is one line)."""


def _sigterm_handler(signum, frame):  # noqa: ARG001 -- required signature
    raise _Terminated()


def run(extra_argv: list[str] | None = None) -> int:
    """The whole launcher. Returns a process exit code."""
    signal.signal(signal.SIGTERM, _sigterm_handler)
    existing = _already_running()
    if existing is not None:
        port = existing.get("port")
        pid = existing.get("pid", "?")
        print(f"app: already running at http://127.0.0.1:{port}/ (pid {pid}). "
              "Refusing to start a second instance against the same vault "
              "(INTENT §5: one writer). Close the existing window first.",
              file=sys.stderr)
        return 1

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    port = _ephemeral_port()
    argv = [sys.executable, str(_RUN_PY), "app", "--host", "127.0.0.1",
            "--port", str(port)] + list(extra_argv or [])
    print(f"app: starting on an ephemeral port ({port})...", file=sys.stderr)
    proc = subprocess.Popen(argv, cwd=str(TOOLKIT_ROOT))
    LOCK_PATH.write_text(json.dumps({
        "port": port, "pid": proc.pid,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }), encoding="utf-8")

    try:
        if not _wait_for_health(port):
            print(f"app: server did not answer /api/health within "
                  f"{HEALTH_TIMEOUT_S}s -- see its output above for why.",
                  file=sys.stderr)
            return 2

        url = f"http://127.0.0.1:{port}/"
        opened = _open_window(url)
        if not opened:
            # The stop condition this exists for: a fighting platform ships the
            # fallback, never a silent exit. The server keeps running and this
            # process blocks on it so closing the launcher (Ctrl+C) is still
            # the one clear way to stop it -- same shape as every other
            # foreground server command in this estate.
            print(f"app: no window backend available on this platform "
                  f"(pywebview needs GTK or Qt; pip install -e '.[desktop]' "
                  "and a system GTK/Qt install may still not be enough on a "
                  "headless box -- that is expected there, not a bug).",
                  file=sys.stderr)
            print(f"app: the server is running. Open this in a browser: {url}",
                  file=sys.stderr)
            try:
                proc.wait()
            except (KeyboardInterrupt, _Terminated):
                pass
        return 0
    except _Terminated:
        print("app: terminated -- shutting down.", file=sys.stderr)
        return 0
    finally:
        # Second instance protection ends here too, not just at startup: an
        # instance that exits (window closed, or the fallback's Ctrl+C) must
        # stop being "the running instance" for the next launch to see.
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        if LOCK_PATH.is_file():
            try:
                LOCK_PATH.unlink()
            except OSError:
                pass

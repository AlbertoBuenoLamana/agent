"""Application discovery and control — replaces AppControl.swift.

Uses wmctrl, xdotool, and /proc for app management.
"""

import subprocess
from dataclasses import dataclass

from .errors import AppNotFound


@dataclass
class AppInfo:
    name: str
    pid: int
    bundleId: str  # Always "" on Linux, kept for JSON compat
    isActive: bool

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "pid": self.pid,
            "bundleId": self.bundleId,
            "isActive": self.isActive,
        }


def _run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
    return result.stdout


def _get_active_window_pid() -> int | None:
    """Get PID of the currently active window."""
    try:
        wid = _run(["xdotool", "getactivewindow"]).strip()
        if wid:
            pid_str = _run(["xdotool", "getwindowpid", wid]).strip()
            return int(pid_str) if pid_str else None
    except (subprocess.TimeoutExpired, ValueError):
        pass
    return None


def list_apps() -> list[AppInfo]:
    """List running GUI applications with windows."""
    output = _run(["wmctrl", "-lp"])
    active_pid = _get_active_window_pid()

    seen_pids: dict[int, str] = {}
    for line in output.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split(None, 5)
        if len(parts) < 5:
            continue
        pid = int(parts[2])
        title = parts[4] if len(parts) > 4 else ""

        # Get process name from /proc
        if pid > 0 and pid not in seen_pids:
            try:
                with open(f"/proc/{pid}/comm") as f:
                    proc_name = f.read().strip()
            except (FileNotFoundError, PermissionError):
                proc_name = title.split(" - ")[-1] if title else f"pid-{pid}"
            seen_pids[pid] = proc_name

    apps = []
    for pid, name in seen_pids.items():
        apps.append(AppInfo(
            name=name,
            pid=pid,
            bundleId="",
            isActive=(pid == active_pid),
        ))

    return sorted(apps, key=lambda a: a.name.lower())


def find(name: str) -> AppInfo | None:
    """Find app by name (case-insensitive)."""
    name_lower = name.lower()
    for app in list_apps():
        if name_lower in app.name.lower():
            return app
    return None


def activate(name: str) -> None:
    """Bring app to foreground."""
    # Try wmctrl first
    result = subprocess.run(
        ["wmctrl", "-a", name],
        capture_output=True, text=True, timeout=5,
    )
    if result.returncode != 0:
        # Fallback: xdotool search
        wids = _run(["xdotool", "search", "--name", name]).strip().split("\n")
        wids = [w for w in wids if w.strip()]
        if not wids:
            raise AppNotFound(f"Application '{name}' not found")
        _run(["xdotool", "windowactivate", "--sync", wids[0]])


def launch(name: str) -> None:
    """Launch an application."""
    try:
        subprocess.Popen(
            [name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except FileNotFoundError:
        # Try with gtk-launch for .desktop files
        result = subprocess.run(
            ["gtk-launch", name],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            raise AppNotFound(f"Could not launch '{name}'")


def frontmost() -> AppInfo | None:
    """Get the currently active/frontmost app."""
    try:
        wid = _run(["xdotool", "getactivewindow"]).strip()
        if not wid:
            return None
        pid_str = _run(["xdotool", "getwindowpid", wid]).strip()
        name_str = _run(["xdotool", "getwindowfocus", "getwindowname"]).strip()
        pid = int(pid_str) if pid_str else 0

        # Get process name
        try:
            with open(f"/proc/{pid}/comm") as f:
                proc_name = f.read().strip()
        except (FileNotFoundError, PermissionError):
            proc_name = name_str.split(" - ")[-1] if name_str else "unknown"

        return AppInfo(name=proc_name, pid=pid, bundleId="", isActive=True)
    except (subprocess.TimeoutExpired, ValueError):
        return None

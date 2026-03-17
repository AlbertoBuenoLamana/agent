"""Window management — replaces WindowControl.swift.

Uses wmctrl and xdotool for window operations.
"""

import subprocess
from dataclasses import dataclass

from .errors import AppNotFound, WindowNotFound, WindowActionFailed
from . import app_control


@dataclass
class WindowInfo:
    app: str
    title: str
    x: int
    y: int
    width: int
    height: int
    isMinimized: bool
    isFullscreen: bool

    def to_dict(self) -> dict:
        return {
            "app": self.app,
            "title": self.title,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "isMinimized": self.isMinimized,
            "isFullscreen": self.isFullscreen,
        }


def _run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
    return result.stdout


def _find_window_ids(app_name: str) -> list[str]:
    """Find X window IDs for an app."""
    app = app_control.find(app_name)
    if not app:
        raise AppNotFound(f"Application '{app_name}' not found")

    output = _run(["wmctrl", "-lGp"])
    wids = []
    for line in output.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split(None, 8)
        if len(parts) < 5:
            continue
        w_pid = int(parts[2])
        if w_pid == app.pid:
            wids.append(parts[0])

    # Fallback: search by name
    if not wids:
        result = _run(["xdotool", "search", "--name", app_name])
        wids = [w.strip() for w in result.strip().split("\n") if w.strip()]

    if not wids:
        raise WindowNotFound(f"No windows found for '{app_name}'")

    return wids


def list_windows(app_name: str) -> list[WindowInfo]:
    """List all windows for an application."""
    app = app_control.find(app_name)
    if not app:
        raise AppNotFound(f"Application '{app_name}' not found")

    output = _run(["wmctrl", "-lGp"])
    windows = []

    for line in output.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split(None, 8)
        if len(parts) < 8:
            continue

        wid = parts[0]
        w_pid = int(parts[2])
        x, y = int(parts[3]), int(parts[4])
        w, h = int(parts[5]), int(parts[6])
        title = parts[8] if len(parts) > 8 else ""

        if w_pid != app.pid:
            continue

        # Check window state via xprop
        is_min = False
        is_full = False
        try:
            xprop = _run(["xprop", "-id", wid, "_NET_WM_STATE"])
            is_min = "_NET_WM_STATE_HIDDEN" in xprop
            is_full = "_NET_WM_STATE_FULLSCREEN" in xprop
        except Exception:
            pass

        windows.append(WindowInfo(
            app=app.name,
            title=title,
            x=x, y=y, width=w, height=h,
            isMinimized=is_min,
            isFullscreen=is_full,
        ))

    return windows


def move(app_name: str, x: int, y: int) -> None:
    """Move app's window to x,y."""
    wids = _find_window_ids(app_name)
    result = subprocess.run(
        ["wmctrl", "-i", "-r", wids[0], "-e", f"0,{x},{y},-1,-1"],
        capture_output=True, text=True, timeout=5,
    )
    if result.returncode != 0:
        raise WindowActionFailed(f"move failed for '{app_name}': {result.stderr}")


def resize(app_name: str, width: int, height: int) -> None:
    """Resize app's window."""
    wids = _find_window_ids(app_name)
    result = subprocess.run(
        ["wmctrl", "-i", "-r", wids[0], "-e", f"0,-1,-1,{width},{height}"],
        capture_output=True, text=True, timeout=5,
    )
    if result.returncode != 0:
        raise WindowActionFailed(f"resize failed for '{app_name}': {result.stderr}")


def minimize(app_name: str) -> None:
    """Minimize app's window."""
    wids = _find_window_ids(app_name)
    # xdotool windowminimize expects decimal window ID
    wid_dec = str(int(wids[0], 16))
    result = subprocess.run(
        ["xdotool", "windowminimize", wid_dec],
        capture_output=True, text=True, timeout=5,
    )
    if result.returncode != 0:
        raise WindowActionFailed(f"minimize failed for '{app_name}'")


def restore(app_name: str) -> None:
    """Restore (un-minimize) app's window."""
    wids = _find_window_ids(app_name)
    result = subprocess.run(
        ["wmctrl", "-i", "-r", wids[0], "-b", "remove,hidden"],
        capture_output=True, text=True, timeout=5,
    )
    # Also activate to bring to front
    subprocess.run(
        ["wmctrl", "-i", "-a", wids[0]],
        capture_output=True, text=True, timeout=5,
    )
    if result.returncode != 0:
        raise WindowActionFailed(f"restore failed for '{app_name}'")


def fullscreen(app_name: str) -> None:
    """Toggle fullscreen for app's window."""
    wids = _find_window_ids(app_name)
    result = subprocess.run(
        ["wmctrl", "-i", "-r", wids[0], "-b", "toggle,fullscreen"],
        capture_output=True, text=True, timeout=5,
    )
    if result.returncode != 0:
        raise WindowActionFailed(f"fullscreen failed for '{app_name}'")


def close(app_name: str) -> None:
    """Close app's window."""
    wids = _find_window_ids(app_name)
    result = subprocess.run(
        ["wmctrl", "-i", "-c", wids[0]],
        capture_output=True, text=True, timeout=5,
    )
    if result.returncode != 0:
        raise WindowActionFailed(f"close failed for '{app_name}'")

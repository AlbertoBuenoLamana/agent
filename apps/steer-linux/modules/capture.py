"""Screenshot and display enumeration — replaces ScreenCapture.swift.

Uses scrot for screenshots, xrandr for display info, wmctrl for window bounds.
"""

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .errors import CaptureFailure, ScreenNotFound, AppNotFound

STORE_DIR = Path("/tmp/steer")


@dataclass
class ScreenInfo:
    index: int
    name: str
    width: int
    height: int
    originX: int
    originY: int
    isMain: bool
    scaleFactor: float

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "name": self.name,
            "width": self.width,
            "height": self.height,
            "originX": self.originX,
            "originY": self.originY,
            "isMain": self.isMain,
            "scaleFactor": self.scaleFactor,
        }


@dataclass
class WindowBounds:
    id: int
    title: str
    x: int
    y: int
    width: int
    height: int

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
        }


def _run(cmd: list[str]) -> str:
    """Run command and return stdout."""
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    if result.returncode != 0:
        raise CaptureFailure(f"Command failed: {' '.join(cmd)}: {result.stderr.strip()}")
    return result.stdout


def capture_screen(snap_id: str, index: int | None = None) -> Path:
    """Capture full screen or specific monitor. Returns path to PNG."""
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    out_path = STORE_DIR / f"{snap_id}.png"

    if index is not None:
        # Capture specific screen region using xrandr info
        screen = screen_info(index)
        if screen is None:
            screens = list_screens()
            raise ScreenNotFound(
                f"Screen {index} not found. Available: {len(screens)} screen(s)"
            )
        # Use scrot with geometry
        _run([
            "scrot", "-a",
            f"{screen.originX},{screen.originY},{screen.width},{screen.height}",
            str(out_path),
        ])
    else:
        _run(["scrot", str(out_path)])

    if not out_path.exists():
        raise CaptureFailure(f"Screenshot not saved to {out_path}")
    return out_path


def capture_app(app_name: str, snap_id: str) -> Path:
    """Capture a specific application window. Returns path to PNG."""
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    out_path = STORE_DIR / f"{snap_id}.png"

    # Find window ID via xdotool
    result = subprocess.run(
        ["xdotool", "search", "--name", app_name],
        capture_output=True, text=True, timeout=5,
    )
    window_ids = result.stdout.strip().split("\n")
    window_ids = [w for w in window_ids if w.strip()]

    if not window_ids:
        raise AppNotFound(f"No window found for '{app_name}'")

    wid = window_ids[0]

    # Use import (ImageMagick) to capture specific window
    try:
        _run(["import", "-window", wid, str(out_path)])
    except CaptureFailure:
        # Fallback: use scrot focused window
        # First activate the window
        subprocess.run(["xdotool", "windowactivate", "--sync", wid],
                       capture_output=True, timeout=5)
        import time
        time.sleep(0.3)
        _run(["scrot", "-u", str(out_path)])

    if not out_path.exists():
        raise CaptureFailure(f"Screenshot not saved to {out_path}")
    return out_path


def list_screens() -> list[ScreenInfo]:
    """Parse xrandr output to enumerate connected displays."""
    output = _run(["xrandr", "--query"])
    screens = []
    idx = 0

    # Match lines like: eDP-1 connected primary 1920x1080+0+0 ...
    # or: HDMI-1 connected 2560x1440+1920+0 ...
    pattern = re.compile(
        r"^(\S+)\s+connected\s+(primary\s+)?(\d+)x(\d+)\+(\d+)\+(\d+)",
        re.MULTILINE,
    )

    for m in pattern.finditer(output):
        name = m.group(1)
        is_primary = m.group(2) is not None
        w, h = int(m.group(3)), int(m.group(4))
        ox, oy = int(m.group(5)), int(m.group(6))

        screens.append(ScreenInfo(
            index=idx,
            name=name,
            width=w,
            height=h,
            originX=ox,
            originY=oy,
            isMain=is_primary,
            scaleFactor=1.0,  # X11 doesn't have per-monitor scale by default
        ))
        idx += 1

    return screens


def screen_info(index: int) -> ScreenInfo | None:
    """Get a specific screen by index."""
    screens = list_screens()
    if 0 <= index < len(screens):
        return screens[index]
    return None


def window_bounds(app_name: str, pid: int | None = None) -> list[WindowBounds]:
    """Get window bounds for an app via wmctrl -lG."""
    output = _run(["wmctrl", "-lGp"])
    windows = []

    for line in output.strip().split("\n"):
        if not line.strip():
            continue
        # Format: 0x04200003  0 1234  0    0    1920 1080 hostname Title text
        parts = line.split(None, 8)
        if len(parts) < 9:
            continue

        wid = int(parts[0], 16)
        w_pid = int(parts[2])
        x, y = int(parts[3]), int(parts[4])
        w, h = int(parts[5]), int(parts[6])
        title = parts[8] if len(parts) > 8 else ""

        # Filter by PID or app name in title
        if pid and w_pid == pid:
            windows.append(WindowBounds(id=wid, title=title, x=x, y=y, width=w, height=h))
        elif app_name and app_name.lower() in title.lower():
            windows.append(WindowBounds(id=wid, title=title, x=x, y=y, width=w, height=h))

    return windows


def translate_coords(x: float, y: float, screen_index: int) -> tuple[int, int]:
    """Translate local screenshot coords to global screen coords."""
    info = screen_info(screen_index)
    if info is None:
        return int(x), int(y)
    return int(x + info.originX), int(y + info.originY)

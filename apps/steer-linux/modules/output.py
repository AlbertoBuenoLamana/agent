"""JSON/text output helper matching Swift steer output patterns."""

import json
import sys


def print_json(data: dict | list) -> None:
    """Print compact JSON to stdout."""
    print(json.dumps(data, separators=(",", ":")))


def print_error(msg: str) -> None:
    """Print error to stderr."""
    print(f"Error: {msg}", file=sys.stderr)


def format_element_row(el: dict) -> str:
    """Format a UI element as a text row: ID  role  label  bounds."""
    label = (el.get("label") or "")[:50]
    bounds = f"({el['x']},{el['y']} {el['width']}x{el['height']})"
    return f"  {el['id']:<6} {el['role']:<14} {label:<50} {bounds}"


def format_window_row(idx: int, win: dict) -> str:
    """Format a window as a text row."""
    title = (win.get("title") or "")[:40]
    bounds = f"({win['x']},{win['y']} {win['width']}x{win['height']})"
    flags = []
    if win.get("isMinimized"):
        flags.append("minimized")
    if win.get("isFullscreen"):
        flags.append("fullscreen")
    flag_str = " " + " ".join(flags) if flags else ""
    return f"  [{idx}] {title:<40} {bounds}{flag_str}"

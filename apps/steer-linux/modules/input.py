"""Mouse and keyboard control via xdotool — replaces MouseControl.swift + Keyboard.swift."""

import subprocess
import time

# Modifier key mapping: macOS → Linux
MODIFIER_MAP = {
    "cmd": "super",
    "command": "super",
    "super": "super",
    "shift": "shift",
    "alt": "alt",
    "option": "alt",
    "ctrl": "ctrl",
    "control": "ctrl",
}

# Button name → xdotool button number
BUTTON_MAP = {
    "left": "1",
    "middle": "2",
    "right": "3",
}

# Key name mapping for xdotool
KEY_MAP = {
    "return": "Return",
    "enter": "Return",
    "tab": "Tab",
    "space": "space",
    "delete": "BackSpace",
    "backspace": "BackSpace",
    "forwarddelete": "Delete",
    "escape": "Escape",
    "left": "Left",
    "right": "Right",
    "up": "Up",
    "down": "Down",
    "home": "Home",
    "end": "End",
    "pageup": "Prior",
    "pagedown": "Next",
    "f1": "F1", "f2": "F2", "f3": "F3", "f4": "F4",
    "f5": "F5", "f6": "F6", "f7": "F7", "f8": "F8",
    "f9": "F9", "f10": "F10", "f11": "F11", "f12": "F12",
}


def _run(cmd: list[str], timeout: int = 5) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return result.stdout


def click(x: int, y: int, button: str = "left", count: int = 1, modifiers: list[str] | None = None) -> None:
    """Click at coordinates with optional modifiers."""
    btn = BUTTON_MAP.get(button, "1")

    if modifiers:
        mod_keys = [MODIFIER_MAP.get(m.lower(), m) for m in modifiers]
        for mk in mod_keys:
            _run(["xdotool", "keydown", mk])

    _run(["xdotool", "mousemove", "--sync", str(x), str(y)])

    for _ in range(count):
        _run(["xdotool", "click", btn])
        if count > 1:
            time.sleep(0.05)

    if modifiers:
        mod_keys = [MODIFIER_MAP.get(m.lower(), m) for m in modifiers]
        for mk in reversed(mod_keys):
            _run(["xdotool", "keyup", mk])


def type_text(text: str) -> None:
    """Type text string."""
    _run(["xdotool", "type", "--delay", "50", "--clearmodifiers", text], timeout=30)


def hotkey(combo: str) -> None:
    """Execute a keyboard shortcut. Parses 'cmd+s' → 'super+s'."""
    parts = combo.lower().split("+")
    keys = []
    for p in parts:
        p = p.strip()
        if p in MODIFIER_MAP:
            keys.append(MODIFIER_MAP[p])
        elif p in KEY_MAP:
            keys.append(KEY_MAP[p])
        else:
            keys.append(p)

    key_combo = "+".join(keys)
    _run(["xdotool", "key", "--clearmodifiers", key_combo])


def scroll(direction: str, lines: int = 3) -> None:
    """Scroll in a direction by N lines."""
    # xdotool: button 4=up, 5=down, 6=left, 7=right
    button_map = {"up": "4", "down": "5", "left": "6", "right": "7"}
    btn = button_map.get(direction.lower(), "5")

    for _ in range(lines):
        _run(["xdotool", "click", btn])
        time.sleep(0.02)


def drag(from_x: int, from_y: int, to_x: int, to_y: int,
         steps: int = 20, modifiers: list[str] | None = None) -> None:
    """Drag from one point to another with smooth interpolation."""
    if modifiers:
        mod_keys = [MODIFIER_MAP.get(m.lower(), m) for m in modifiers]
        for mk in mod_keys:
            _run(["xdotool", "keydown", mk])

    _run(["xdotool", "mousemove", "--sync", str(from_x), str(from_y)])
    _run(["xdotool", "mousedown", "1"])

    # Smooth interpolation
    for i in range(1, steps + 1):
        t = i / steps
        ix = int(from_x + (to_x - from_x) * t)
        iy = int(from_y + (to_y - from_y) * t)
        _run(["xdotool", "mousemove", "--sync", str(ix), str(iy)])
        time.sleep(0.01)

    _run(["xdotool", "mouseup", "1"])

    if modifiers:
        mod_keys = [MODIFIER_MAP.get(m.lower(), m) for m in modifiers]
        for mk in reversed(mod_keys):
            _run(["xdotool", "keyup", mk])


def move_to(x: int, y: int) -> None:
    """Move cursor to coordinates."""
    _run(["xdotool", "mousemove", "--sync", str(x), str(y)])


def key_down(key: str) -> None:
    """Press and hold a key."""
    k = MODIFIER_MAP.get(key.lower(), KEY_MAP.get(key.lower(), key))
    _run(["xdotool", "keydown", k])


def key_up(key: str) -> None:
    """Release a key."""
    k = MODIFIER_MAP.get(key.lower(), KEY_MAP.get(key.lower(), key))
    _run(["xdotool", "keyup", k])


def parse_modifiers(combo: str) -> list[str]:
    """Parse modifier string like 'cmd+shift' into a list."""
    if not combo:
        return []
    return [MODIFIER_MAP.get(p.strip().lower(), p.strip()) for p in combo.split("+")]

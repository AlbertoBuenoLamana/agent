"""Snapshot cache for UI elements — matches ElementStore.swift logic.

Stores snapshots in /tmp/steer/<snapid>.json and .png.
Elements use role-prefixed IDs: B1, T2, S3, etc.
"""

import json
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path

from .errors import ElementNotFound, NoSnapshot

STORE_DIR = Path("/tmp/steer")

# Role prefix mapping — same as Swift original
ROLE_PREFIXES = {
    "push button": "B",
    "button": "B",
    "text": "T",
    "text field": "T",
    "entry": "T",
    "password text": "T",
    "label": "S",
    "static text": "S",
    "image": "I",
    "icon": "I",
    "check box": "C",
    "check menu item": "C",
    "radio button": "R",
    "radio menu item": "R",
    "combo box": "P",
    "popup button": "P",
    "slider": "SL",
    "link": "L",
    "menu item": "M",
    "menu": "M",
    "page tab": "TB",
    "page tab list": "TB",
    "tool bar button": "B",
    "toggle button": "B",
    "cell": "E",
    "ocrtext": "O",
}


@dataclass
class UIElement:
    id: str
    role: str
    label: str | None
    value: str | None
    x: int
    y: int
    width: int
    height: int
    isEnabled: bool
    depth: int

    @property
    def center_x(self) -> int:
        return self.x + self.width // 2

    @property
    def center_y(self) -> int:
        return self.y + self.height // 2

    def to_dict(self) -> dict:
        return asdict(self)


def role_prefix(role: str) -> str:
    """Get the ID prefix for a given role name."""
    return ROLE_PREFIXES.get(role.lower(), "E")


def assign_ids(elements: list[dict]) -> list[dict]:
    """Assign role-prefixed IDs (B1, T2, S3) to elements."""
    counters: dict[str, int] = {}
    for el in elements:
        prefix = role_prefix(el.get("role", ""))
        counters[prefix] = counters.get(prefix, 0) + 1
        el["id"] = f"{prefix}{counters[prefix]}"
    return elements


# In-memory cache
_cache: dict[str, list[dict]] = {}
_latest_id: str | None = None


def generate_id() -> str:
    """Generate 8-char snapshot ID."""
    return uuid.uuid4().hex[:8]


def save(snap_id: str, elements: list[dict], screenshot_path: str | None = None) -> Path:
    """Store snapshot to disk and in-memory cache."""
    global _latest_id
    STORE_DIR.mkdir(parents=True, exist_ok=True)

    _cache[snap_id] = elements
    _latest_id = snap_id

    json_path = STORE_DIR / f"{snap_id}.json"
    json_path.write_text(json.dumps(elements, separators=(",", ":")))

    return json_path


def load(snap_id: str) -> list[dict]:
    """Load snapshot from cache or disk."""
    if snap_id in _cache:
        return _cache[snap_id]

    json_path = STORE_DIR / f"{snap_id}.json"
    if json_path.exists():
        elements = json.loads(json_path.read_text())
        _cache[snap_id] = elements
        return elements

    raise NoSnapshot(f"Snapshot '{snap_id}' not found")


def latest() -> tuple[str, list[dict]]:
    """Get the most recent snapshot."""
    if _latest_id and _latest_id in _cache:
        return _latest_id, _cache[_latest_id]

    # Fall back to disk — find newest .json by mtime
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    json_files = sorted(STORE_DIR.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not json_files:
        raise NoSnapshot("No snapshots available. Run 'steer see' first.")

    snap_id = json_files[0].stem
    return snap_id, load(snap_id)


def resolve(query: str, snap_id: str | None = None) -> dict:
    """Find element by ID, exact label, or partial label match.

    Search priority: exact ID → exact label → partial label (contains).
    """
    if snap_id:
        elements = load(snap_id)
        sid = snap_id
    else:
        sid, elements = latest()

    q = query.strip()
    q_lower = q.lower()

    # Exact ID match
    for el in elements:
        if el["id"].lower() == q_lower:
            return el

    # Exact label match
    for el in elements:
        label = (el.get("label") or "").lower()
        value = (el.get("value") or "").lower()
        if label == q_lower or value == q_lower:
            return el

    # Partial label match
    for el in elements:
        label = (el.get("label") or "").lower()
        value = (el.get("value") or "").lower()
        if q_lower in label or q_lower in value:
            return el

    raise ElementNotFound(
        f"Element '{query}' not found in snapshot '{sid}'. "
        f"Run 'steer see' to refresh the element tree."
    )

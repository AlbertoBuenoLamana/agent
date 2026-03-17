"""Accessibility tree traversal — replaces AccessibilityTree.swift.

Uses AT-SPI2 via gi.repository.Atspi (python3-atspi package) for reading
the accessibility tree of running applications on Linux.
"""

from .element_store import ROLE_PREFIXES
from .errors import AppNotFound

# AT-SPI2 role name → our prefix mapping
_ROLE_MAP = {
    "push button": "B",
    "toggle button": "B",
    "text": "T",
    "entry": "T",
    "password text": "T",
    "label": "S",
    "static": "S",
    "image": "I",
    "icon": "I",
    "check box": "C",
    "check menu item": "C",
    "radio button": "R",
    "radio menu item": "R",
    "combo box": "P",
    "slider": "SL",
    "link": "L",
    "menu item": "M",
    "menu": "M",
    "page tab": "TB",
    "page tab list": "TB",
}

# Roles we consider interactive (filter for cleaner output)
INTERACTIVE_ROLES = {
    "push button", "toggle button", "text", "entry", "password text",
    "check box", "check menu item", "radio button", "radio menu item",
    "combo box", "slider", "link", "menu item", "page tab",
    "tool bar button", "cell", "label", "static", "image", "icon",
}


def _get_atspi():
    """Lazy import of AT-SPI2 bindings."""
    try:
        import gi
        gi.require_version("Atspi", "2.0")
        from gi.repository import Atspi
        return Atspi
    except (ImportError, ValueError):
        return None


def is_accessibility_granted() -> bool:
    """Check if AT-SPI2 is available. Usually enabled by default on Linux."""
    Atspi = _get_atspi()
    if Atspi is None:
        return False
    try:
        desktop = Atspi.get_desktop(0)
        return desktop is not None
    except Exception:
        return False


def _find_app(app_name: str):
    """Find an application in the AT-SPI2 registry by name."""
    Atspi = _get_atspi()
    if Atspi is None:
        raise AppNotFound(f"AT-SPI2 not available. Install python3-atspi.")

    desktop = Atspi.get_desktop(0)
    name_lower = app_name.lower()

    for i in range(desktop.get_child_count()):
        child = desktop.get_child_at_index(i)
        if child is None:
            continue
        child_name = (child.get_name() or "").lower()
        if name_lower in child_name or child_name in name_lower:
            return child

    raise AppNotFound(f"Application '{app_name}' not found in AT-SPI2 registry")


def _role_name(accessible) -> str:
    """Get the role name string from an AT-SPI2 accessible object."""
    try:
        return accessible.get_role_name() or ""
    except Exception:
        return ""


def _get_bounds(accessible) -> tuple[int, int, int, int]:
    """Get bounding box (x, y, w, h) from accessible component."""
    try:
        component = accessible.get_component_iface()
        if component:
            rect = component.get_extents(0)  # 0 = ATSPI_COORD_TYPE_SCREEN
            return rect.x, rect.y, rect.width, rect.height
    except Exception:
        pass
    return 0, 0, 0, 0


def walk(app_name: str, max_depth: int = 15) -> list[dict]:
    """Traverse the accessibility tree and return UI elements.

    Assigns role-prefixed IDs (B1, T2, S3) matching Swift original scheme.
    """
    app = _find_app(app_name)
    elements = []
    counters: dict[str, int] = {}

    def _traverse(node, depth: int):
        if depth > max_depth or node is None:
            return

        role = _role_name(node)
        name = ""
        value = None

        try:
            name = node.get_name() or ""
        except Exception:
            pass

        try:
            text_iface = node.get_text_iface()
            if text_iface:
                value = text_iface.get_text(0, text_iface.get_character_count())
        except Exception:
            pass

        try:
            value_iface = node.get_value_iface()
            if value_iface and value is None:
                value = str(value_iface.get_current_value())
        except Exception:
            pass

        x, y, w, h = _get_bounds(node)

        # Check if element is enabled
        is_enabled = True
        try:
            state_set = node.get_state_set()
            if state_set:
                # ATSPI_STATE_SENSITIVE = 17
                is_enabled = state_set.contains(17)
        except Exception:
            pass

        # Only include elements with some content or interactive role
        role_lower = role.lower()
        if (name or value) or role_lower in INTERACTIVE_ROLES:
            prefix = _ROLE_MAP.get(role_lower, "E")
            counters[prefix] = counters.get(prefix, 0) + 1
            el_id = f"{prefix}{counters[prefix]}"

            elements.append({
                "id": el_id,
                "role": role,
                "label": name if name else None,
                "value": value,
                "x": x,
                "y": y,
                "width": w,
                "height": h,
                "isEnabled": is_enabled,
                "depth": depth,
            })

        # Recurse into children
        try:
            count = node.get_child_count()
            for i in range(count):
                child = node.get_child_at_index(i)
                _traverse(child, depth + 1)
        except Exception:
            pass

    _traverse(app, 0)
    return elements


def focused_element(app_name: str) -> dict | None:
    """Get the currently focused UI element for an app."""
    Atspi = _get_atspi()
    if Atspi is None:
        return None

    app = _find_app(app_name)

    def _find_focused(node) -> dict | None:
        if node is None:
            return None

        try:
            state_set = node.get_state_set()
            # ATSPI_STATE_FOCUSED = 12
            if state_set and state_set.contains(12):
                role = _role_name(node)
                name = ""
                value = None
                try:
                    name = node.get_name() or ""
                except Exception:
                    pass
                try:
                    text_iface = node.get_text_iface()
                    if text_iface:
                        value = text_iface.get_text(0, text_iface.get_character_count())
                except Exception:
                    pass

                x, y, w, h = _get_bounds(node)

                is_enabled = True
                try:
                    is_enabled = state_set.contains(17)
                except Exception:
                    pass

                return {
                    "id": "F0",
                    "role": role,
                    "label": name if name else None,
                    "value": value,
                    "x": x, "y": y,
                    "width": w, "height": h,
                    "isEnabled": is_enabled,
                    "depth": 0,
                }
        except Exception:
            pass

        try:
            count = node.get_child_count()
            for i in range(count):
                child = node.get_child_at_index(i)
                result = _find_focused(child)
                if result:
                    return result
        except Exception:
            pass

        return None

    return _find_focused(app)

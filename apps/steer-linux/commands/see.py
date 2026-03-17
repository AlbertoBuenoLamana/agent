"""see — Capture screenshot + accessibility tree."""

import sys

import click

from modules import element_store, capture, accessibility, ocr_engine
from modules.errors import SteerError
from modules.output import print_json, print_error, format_element_row


@click.command()
@click.option("--app", default=None, help="Target app name; default: frontmost")
@click.option("--screen", "screen_idx", type=int, default=None, help="Screen index to capture")
@click.option("--ocr", "use_ocr", is_flag=True, default=False, help="Run OCR when accessibility tree is empty")
@click.option("--role", default=None, help="Filter elements by role")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output JSON")
def see(app, screen_idx, use_ocr, role, as_json):
    """Capture screenshot + accessibility tree for an app or screen."""
    try:
        from modules import app_control

        snap_id = element_store.generate_id()

        # Determine app name
        if app is None and screen_idx is None:
            frontmost = app_control.frontmost()
            app = frontmost.name if frontmost else "desktop"

        # Capture screenshot
        if screen_idx is not None and app is None:
            screenshot = capture.capture_screen(snap_id, screen_idx)
        elif app:
            try:
                screenshot = capture.capture_app(app, snap_id)
            except SteerError:
                screenshot = capture.capture_screen(snap_id)
        else:
            screenshot = capture.capture_screen(snap_id)

        # Get accessibility tree
        elements = []
        if app and screen_idx is None:
            try:
                elements = accessibility.walk(app)
            except SteerError:
                pass

        # OCR fallback if tree is empty
        if not elements and use_ocr:
            ocr_results = ocr_engine.recognize(str(screenshot))
            elements = ocr_engine.to_elements(ocr_results)

        # Role filter
        if role and elements:
            role_lower = role.lower()
            elements = [e for e in elements if role_lower in e.get("role", "").lower()]

        # Assign IDs if not already assigned
        for el in elements:
            if not el.get("id"):
                elements = element_store.assign_ids(elements)
                break

        # Get window bounds
        windows = []
        if app:
            try:
                bounds = capture.window_bounds(app)
                windows = [b.to_dict() for b in bounds]
            except SteerError:
                pass

        # Save snapshot
        element_store.save(snap_id, elements, str(screenshot))

        if as_json:
            print_json({
                "snapshot": snap_id,
                "app": app or "",
                "screenshot": str(screenshot),
                "count": len(elements),
                "windows": windows,
                "elements": elements,
            })
        else:
            print(f"Snapshot: {snap_id}")
            print(f"App: {app or 'desktop'}")
            print(f"Screenshot: {screenshot}")
            print(f"Elements: {len(elements)}")
            if windows:
                for w in windows:
                    print(f"  Window: {w.get('title', '')} ({w['x']},{w['y']} {w['width']}x{w['height']})")
            for el in elements:
                print(format_element_row(el))

    except SteerError as e:
        print_error(str(e))
        sys.exit(1)

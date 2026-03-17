"""wait — Wait for app launch or element appearance."""

import sys
import time

import click

from modules import element_store, accessibility
from modules.errors import SteerError, WaitTimeout
from modules.output import print_json, print_error


@click.command()
@click.option("--for", "target", default=None, help="Element ID or label to wait for")
@click.option("--app", default=None, help="App name to wait for")
@click.option("--timeout", type=float, default=10, help="Max wait time in seconds")
@click.option("--interval", type=float, default=0.5, help="Poll interval in seconds")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output JSON")
def wait(target, app, timeout, interval, as_json):
    """Wait for an app to launch or an element to appear."""
    try:
        if not target and not app:
            raise SteerError("Provide --app, --for, or both")

        from modules import app_control

        deadline = time.monotonic() + timeout

        # Wait for app only
        if app and not target:
            while time.monotonic() < deadline:
                found = app_control.find(app)
                if found:
                    if as_json:
                        print_json({"action": "wait", "condition": "app", "app": app, "ok": True})
                    else:
                        print(f"Found app: {app}")
                    return
                time.sleep(interval)

            if as_json:
                print_json({"action": "wait", "condition": "app", "app": app, "ok": False, "error": "timeout"})
            else:
                print_error(f"Timeout waiting for app '{app}' after {timeout}s")
            sys.exit(1)

        # Wait for element (optionally in specific app)
        while time.monotonic() < deadline:
            try:
                if app:
                    elements = accessibility.walk(app)
                else:
                    frontmost = app_control.frontmost()
                    if not frontmost:
                        time.sleep(interval)
                        continue
                    app = frontmost.name
                    elements = accessibility.walk(app)

                # Search: exact ID → exact label → partial label
                q_lower = target.lower()
                for el in elements:
                    if el["id"].lower() == q_lower:
                        if as_json:
                            print_json({"action": "wait", "condition": "element", "id": el["id"],
                                        "label": el.get("label") or "", "app": app, "ok": True})
                        else:
                            print(f"Found {el['id']} \"{el.get('label', '')}\" in {app}")
                        return

                for el in elements:
                    label = (el.get("label") or "").lower()
                    if label == q_lower:
                        if as_json:
                            print_json({"action": "wait", "condition": "element", "id": el["id"],
                                        "label": el.get("label") or "", "app": app, "ok": True})
                        else:
                            print(f"Found {el['id']} \"{el.get('label', '')}\" in {app}")
                        return

                for el in elements:
                    label = (el.get("label") or "").lower()
                    if q_lower in label:
                        if as_json:
                            print_json({"action": "wait", "condition": "element", "id": el["id"],
                                        "label": el.get("label") or "", "app": app, "ok": True})
                        else:
                            print(f"Found {el['id']} \"{el.get('label', '')}\" in {app}")
                        return

            except SteerError:
                pass

            time.sleep(interval)

        if as_json:
            print_json({"action": "wait", "condition": "element", "app": app or "",
                         "ok": False, "error": "timeout"})
        else:
            print_error(f"Timeout waiting for '{target}' after {timeout}s")
        sys.exit(1)

    except SteerError as e:
        print_error(str(e))
        sys.exit(1)

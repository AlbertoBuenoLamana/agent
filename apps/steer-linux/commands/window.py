"""window — Manage app windows."""

import sys

import click

from modules import window_control
from modules.errors import SteerError
from modules.output import print_json, print_error, format_window_row


@click.command()
@click.argument("action", type=click.Choice(["list", "move", "resize", "minimize", "restore", "fullscreen", "close"]))
@click.argument("app")
@click.option("-x", type=float, default=None, help="X position (for move)")
@click.option("-y", type=float, default=None, help="Y position (for move)")
@click.option("-w", "--width", type=float, default=None, help="Width (for resize)")
@click.option("-h", "--height", type=float, default=None, help="Height (for resize)")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output JSON")
def window(action, app, x, y, width, height, as_json):
    """Manage app windows: list, move, resize, minimize, restore, fullscreen, close."""
    try:
        if action == "list":
            windows = window_control.list_windows(app)
            if as_json:
                print_json([w.to_dict() for w in windows])
            else:
                for i, w in enumerate(windows):
                    print(format_window_row(i, w.to_dict()))

        elif action == "move":
            if x is None or y is None:
                raise SteerError("--x and --y required for move")
            window_control.move(app, int(x), int(y))
            if as_json:
                print_json({"action": "move", "app": app, "x": int(x), "y": int(y), "ok": True})
            else:
                print(f"Moved {app} to ({int(x)}, {int(y)})")

        elif action == "resize":
            if width is None or height is None:
                raise SteerError("--width and --height required for resize")
            window_control.resize(app, int(width), int(height))
            if as_json:
                print_json({"action": "resize", "app": app, "width": int(width), "height": int(height), "ok": True})
            else:
                print(f"Resized {app} to {int(width)}x{int(height)}")

        elif action == "minimize":
            window_control.minimize(app)
            if as_json:
                print_json({"action": "minimize", "app": app, "ok": True})
            else:
                print(f"Minimized {app}")

        elif action == "restore":
            window_control.restore(app)
            if as_json:
                print_json({"action": "restore", "app": app, "ok": True})
            else:
                print(f"Restored {app}")

        elif action == "fullscreen":
            window_control.fullscreen(app)
            if as_json:
                print_json({"action": "fullscreen", "app": app, "ok": True})
            else:
                print(f"Toggled fullscreen for {app}")

        elif action == "close":
            window_control.close(app)
            if as_json:
                print_json({"action": "close", "app": app, "ok": True})
            else:
                print(f"Closed {app}")

    except SteerError as e:
        print_error(str(e))
        sys.exit(1)

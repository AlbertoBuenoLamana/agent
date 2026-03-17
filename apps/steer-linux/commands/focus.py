"""focus — Show currently focused UI element."""

import sys

import click

from modules import accessibility
from modules.errors import SteerError
from modules.output import print_json, print_error


@click.command()
@click.option("--app", default=None, help="Target app; default: frontmost")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output JSON")
def focus(app, as_json):
    """Show the currently focused UI element."""
    try:
        from modules import app_control

        if app is None:
            frontmost = app_control.frontmost()
            app = frontmost.name if frontmost else None

        if not app:
            raise SteerError("No active application found")

        focused = accessibility.focused_element(app)

        if as_json:
            print_json({
                "app": app,
                "focused": focused,
            })
        else:
            print(f"App: {app}")
            if focused:
                label = focused.get("label") or "(none)"
                role = focused.get("role", "")
                bounds = f"({focused['x']},{focused['y']} {focused['width']}x{focused['height']})"
                value = focused.get("value") or ""
                print(f"  Focused: {role} \"{label}\" {bounds}")
                if value:
                    print(f"  Value: {value}")
            else:
                print("  Focused: (none)")

    except SteerError as e:
        print_error(str(e))
        sys.exit(1)

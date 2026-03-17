"""apps — List, launch, or activate applications."""

import sys

import click

from modules import app_control
from modules.errors import SteerError
from modules.output import print_json, print_error


@click.command()
@click.argument("action", default="list", type=click.Choice(["list", "launch", "activate"]))
@click.argument("name", default=None, required=False)
@click.option("--json", "as_json", is_flag=True, default=False, help="Output JSON")
def apps(action, name, as_json):
    """List running apps, launch, or activate an app."""
    try:
        if action == "list":
            app_list = app_control.list_apps()
            if as_json:
                print_json([a.to_dict() for a in app_list])
            else:
                for a in app_list:
                    active = " *" if a.isActive else ""
                    print(f"  {a.name:<25} {a.pid}{active}")

        elif action == "launch":
            if not name:
                raise SteerError("App name required for launch")
            app_control.launch(name)
            if as_json:
                print_json({"action": "launch", "app": name, "ok": True})
            else:
                print(f"Launched {name}")

        elif action == "activate":
            if not name:
                raise SteerError("App name required for activate")
            app_control.activate(name)
            if as_json:
                print_json({"action": "activate", "app": name, "ok": True})
            else:
                print(f"Activated {name}")

    except SteerError as e:
        print_error(str(e))
        sys.exit(1)

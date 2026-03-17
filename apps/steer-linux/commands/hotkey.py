"""hotkey — Press key combination."""

import sys

import click

from modules import input as mouse_kb
from modules.output import print_json, print_error


@click.command()
@click.argument("combo")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output JSON")
def hotkey(combo, as_json):
    """Press a keyboard shortcut (e.g., cmd+s, ctrl+shift+n, return)."""
    try:
        mouse_kb.hotkey(combo)

        if as_json:
            print_json({
                "action": "hotkey",
                "combo": combo,
                "ok": True,
            })
        else:
            print(f"Pressed {combo}")

    except Exception as e:
        print_error(str(e))
        sys.exit(1)

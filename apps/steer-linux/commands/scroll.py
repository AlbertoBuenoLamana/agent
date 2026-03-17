"""scroll — Scroll in direction by N lines."""

import sys

import click

from modules import input as mouse_kb
from modules.output import print_json, print_error


@click.command()
@click.argument("direction", type=click.Choice(["up", "down", "left", "right"]))
@click.argument("lines", type=int, default=3)
@click.option("--json", "as_json", is_flag=True, default=False, help="Output JSON")
def scroll(direction, lines, as_json):
    """Scroll in a direction by N lines."""
    try:
        mouse_kb.scroll(direction, lines)

        if as_json:
            print_json({
                "action": "scroll",
                "direction": direction,
                "lines": lines,
                "ok": True,
            })
        else:
            print(f"Scrolled {direction} {lines} lines")

    except Exception as e:
        print_error(str(e))
        sys.exit(1)

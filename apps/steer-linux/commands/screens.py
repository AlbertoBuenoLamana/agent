"""screens — List connected displays."""

import sys

import click

from modules import capture
from modules.output import print_json, print_error


@click.command()
@click.option("--json", "as_json", is_flag=True, default=False, help="Output JSON")
def screens(as_json):
    """List connected displays with resolution and position."""
    try:
        screen_list = capture.list_screens()

        if as_json:
            print_json([s.to_dict() for s in screen_list])
        else:
            for s in screen_list:
                main_flag = " (main)" if s.isMain else ""
                print(f"  [{s.index}] {s.name:<30} {s.width}x{s.height} +{s.originX}+{s.originY} scale={s.scaleFactor}{main_flag}")

    except Exception as e:
        print_error(str(e))
        sys.exit(1)

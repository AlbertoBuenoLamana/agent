"""drag — Drag from one element/point to another."""

import sys

import click

from modules import element_store, input as mouse_kb, capture
from modules.errors import SteerError
from modules.output import print_json, print_error


@click.command()
@click.option("--from", "from_target", default=None, help="Source element ID or label")
@click.option("--from-x", type=float, default=None, help="Source X coordinate")
@click.option("--from-y", type=float, default=None, help="Source Y coordinate")
@click.option("--to", "to_target", default=None, help="Destination element ID or label")
@click.option("--to-x", type=float, default=None, help="Destination X coordinate")
@click.option("--to-y", type=float, default=None, help="Destination Y coordinate")
@click.option("--snapshot", default=None, help="Snapshot ID")
@click.option("--screen", "screen_idx", type=int, default=None, help="Screen index")
@click.option("--modifier", default=None, help="Modifier keys")
@click.option("--steps", type=int, default=20, help="Intermediate drag points")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output JSON")
def drag(from_target, from_x, from_y, to_target, to_x, to_y, snapshot, screen_idx, modifier, steps, as_json):
    """Drag from source to destination."""
    try:
        # Resolve source
        if from_target:
            el = element_store.resolve(from_target, snapshot)
            fx = el["x"] + el["width"] // 2
            fy = el["y"] + el["height"] // 2
        elif from_x is not None and from_y is not None:
            fx, fy = int(from_x), int(from_y)
        else:
            raise SteerError("Provide --from <element> or --from-x/--from-y")

        # Resolve destination
        if to_target:
            el = element_store.resolve(to_target, snapshot)
            tx = el["x"] + el["width"] // 2
            ty = el["y"] + el["height"] // 2
        elif to_x is not None and to_y is not None:
            tx, ty = int(to_x), int(to_y)
        else:
            raise SteerError("Provide --to <element> or --to-x/--to-y")

        # Translate coords
        if screen_idx is not None:
            fx, fy = capture.translate_coords(fx, fy, screen_idx)
            tx, ty = capture.translate_coords(tx, ty, screen_idx)

        modifiers = mouse_kb.parse_modifiers(modifier) if modifier else None
        mouse_kb.drag(fx, fy, tx, ty, steps=steps, modifiers=modifiers)

        if as_json:
            print_json({
                "action": "drag",
                "fromX": fx, "fromY": fy,
                "toX": tx, "toY": ty,
                "ok": True,
            })
        else:
            mod_str = f"[{modifier}] " if modifier else ""
            print(f"{mod_str}Dragged ({fx},{fy}) -> ({tx},{ty})")

    except SteerError as e:
        print_error(str(e))
        sys.exit(1)

"""click — Click element by ID, label, or coordinates."""

import sys

import click

from modules import element_store, input as mouse_kb, capture
from modules.errors import SteerError
from modules.output import print_json, print_error


@click.command("click")
@click.option("--on", "target", default=None, help="Element ID or label to click")
@click.option("-x", type=float, default=None, help="X coordinate")
@click.option("-y", type=float, default=None, help="Y coordinate")
@click.option("--snapshot", default=None, help="Snapshot ID to resolve element from")
@click.option("--screen", "screen_idx", type=int, default=None, help="Screen index for coord translation")
@click.option("--double", "is_double", is_flag=True, default=False, help="Double-click")
@click.option("--right", "is_right", is_flag=True, default=False, help="Right-click")
@click.option("--middle", "is_middle", is_flag=True, default=False, help="Middle-click")
@click.option("--modifier", default=None, help="Modifier keys: cmd, shift, alt, ctrl (combine with +)")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output JSON")
def click_cmd(target, x, y, snapshot, screen_idx, is_double, is_right, is_middle, modifier, as_json):
    """Click element by ID, label, or x/y coordinates."""
    try:
        if is_right and is_middle:
            raise SteerError("Cannot combine --right and --middle")

        click_x, click_y = None, None
        label = ""

        if target:
            el = element_store.resolve(target, snapshot)
            click_x = el["x"] + el["width"] // 2
            click_y = el["y"] + el["height"] // 2
            label = el.get("label") or el.get("id", "")
        elif x is not None and y is not None:
            click_x, click_y = int(x), int(y)
            label = f"({click_x},{click_y})"
        else:
            raise SteerError("Provide --on <element> or -x/-y coordinates")

        # Translate coords if screen specified
        if screen_idx is not None:
            click_x, click_y = capture.translate_coords(click_x, click_y, screen_idx)

        # Determine button
        button = "left"
        if is_right:
            button = "right"
        elif is_middle:
            button = "middle"

        count = 2 if is_double else 1
        modifiers = mouse_kb.parse_modifiers(modifier) if modifier else None

        mouse_kb.click(click_x, click_y, button=button, count=count, modifiers=modifiers)

        if as_json:
            print_json({
                "action": "click",
                "x": click_x,
                "y": click_y,
                "label": label,
                "ok": True,
            })
        else:
            verb = "Double-clicked" if is_double else "Right-clicked" if is_right else "Clicked"
            mod_str = f"[{modifier}] " if modifier else ""
            print(f"{mod_str}{verb} {label} at ({click_x}, {click_y})")

    except SteerError as e:
        print_error(str(e))
        sys.exit(1)

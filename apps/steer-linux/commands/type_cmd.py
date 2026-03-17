"""type — Type text into focused or target element."""

import sys
import time

import click

from modules import element_store, input as mouse_kb, capture
from modules.errors import SteerError
from modules.output import print_json, print_error


@click.command("type")
@click.argument("text")
@click.option("--into", "target", default=None, help="Target element ID or label; clicks to focus first")
@click.option("--snapshot", default=None, help="Snapshot ID")
@click.option("--screen", "screen_idx", type=int, default=None, help="Screen index for coord translation")
@click.option("--clear", "do_clear", is_flag=True, default=False, help="Clear field first (Ctrl+A, Delete)")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output JSON")
def type_cmd(text, target, snapshot, screen_idx, do_clear, as_json):
    """Type text into focused element or specified target."""
    try:
        if target:
            el = element_store.resolve(target, snapshot)
            cx = el["x"] + el["width"] // 2
            cy = el["y"] + el["height"] // 2
            if screen_idx is not None:
                cx, cy = capture.translate_coords(cx, cy, screen_idx)
            mouse_kb.click(cx, cy)
            time.sleep(0.1)

        if do_clear:
            # Select all + delete (ctrl+a on Linux, not cmd+a)
            mouse_kb.hotkey("ctrl+a")
            time.sleep(0.05)
            mouse_kb.hotkey("delete")
            time.sleep(0.05)

        mouse_kb.type_text(text)

        if as_json:
            print_json({
                "action": "type",
                "text": text,
                "ok": True,
            })
        else:
            into_str = f" into {target}" if target else ""
            print(f'Typed "{text}"{into_str}')

    except SteerError as e:
        print_error(str(e))
        sys.exit(1)

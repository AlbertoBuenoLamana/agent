"""ocr — Extract text via OCR."""

import sys

import click

from modules import element_store, capture, ocr_engine
from modules.errors import SteerError
from modules.output import print_json, print_error


@click.command()
@click.option("--image", "image_path", default=None, help="Path to PNG file; default: captures fresh")
@click.option("--app", default=None, help="Target app name; default: frontmost")
@click.option("--screen", "screen_idx", type=int, default=None, help="Screen index to capture")
@click.option("--confidence", type=float, default=0.5, help="Minimum confidence threshold (0.0-1.0)")
@click.option("--store", "do_store", is_flag=True, default=False, help="Save OCR results as snapshot for click --on")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output JSON")
def ocr(image_path, app, screen_idx, confidence, do_store, as_json):
    """Extract text from screenshot via OCR."""
    try:
        from modules import app_control

        snap_id = element_store.generate_id()

        # Get screenshot if no image provided
        if image_path is None:
            if app:
                try:
                    image_path = str(capture.capture_app(app, snap_id))
                except SteerError:
                    image_path = str(capture.capture_screen(snap_id))
            elif screen_idx is not None:
                image_path = str(capture.capture_screen(snap_id, screen_idx))
            else:
                frontmost = app_control.frontmost()
                app = frontmost.name if frontmost else "desktop"
                image_path = str(capture.capture_screen(snap_id))

        results = ocr_engine.recognize(image_path, min_confidence=confidence)

        # Store as snapshot if requested
        snapshot_id = None
        if do_store:
            elements = ocr_engine.to_elements(results)
            element_store.save(snap_id, elements, image_path)
            snapshot_id = snap_id

        if as_json:
            data = {
                "app": app or "",
                "count": len(results),
                "results": [r.to_dict() for r in results],
            }
            if snapshot_id:
                data["snapshot"] = snapshot_id
            print_json(data)
        else:
            print(f"App: {app or 'desktop'}")
            print(f"Regions: {len(results)}")
            if snapshot_id:
                print(f"Snapshot: {snapshot_id}")
            for r in results:
                text_preview = r.text[:60]
                print(f"  {text_preview:<60} ({r.x},{r.y} {r.width}x{r.height}) conf={r.confidence:.2f}")

    except SteerError as e:
        print_error(str(e))
        sys.exit(1)

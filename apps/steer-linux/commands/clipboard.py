"""clipboard — Read/write system clipboard."""

import subprocess
import sys
import uuid
from pathlib import Path

import click

from modules.errors import SteerError, ClipboardEmpty
from modules.output import print_json, print_error

STORE_DIR = Path("/tmp/steer")


def _read_text() -> str:
    result = subprocess.run(
        ["xclip", "-selection", "clipboard", "-o"],
        capture_output=True, text=True, timeout=5,
    )
    if result.returncode != 0 or not result.stdout:
        raise ClipboardEmpty("Clipboard is empty or has no text")
    return result.stdout


def _write_text(text: str) -> None:
    proc = subprocess.Popen(
        ["xclip", "-selection", "clipboard"],
        stdin=subprocess.PIPE,
    )
    proc.communicate(input=text.encode())


def _read_image(save_to: str | None = None) -> str:
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    if save_to is None:
        save_to = str(STORE_DIR / f"clipboard-{uuid.uuid4().hex[:8]}.png")

    result = subprocess.run(
        ["xclip", "-selection", "clipboard", "-t", "image/png", "-o"],
        capture_output=True, timeout=5,
    )
    if result.returncode != 0 or not result.stdout:
        raise ClipboardEmpty("Clipboard has no image content")

    Path(save_to).write_bytes(result.stdout)
    return save_to


def _write_image(file_path: str) -> None:
    if not Path(file_path).exists():
        raise SteerError(f"File not found: {file_path}")
    subprocess.run(
        ["xclip", "-selection", "clipboard", "-t", "image/png", "-i", file_path],
        capture_output=True, timeout=5,
    )


@click.command()
@click.argument("action", type=click.Choice(["read", "write"]))
@click.argument("text", default=None, required=False)
@click.option("--type", "content_type", default="text", type=click.Choice(["text", "image"]), help="Content type")
@click.option("--file", "file_path", default=None, help="File path for image read/write")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output JSON")
def clipboard(action, text, content_type, file_path, as_json):
    """Read or write system clipboard (text or image)."""
    try:
        if action == "read":
            if content_type == "text":
                content = _read_text()
                if as_json:
                    print_json({"action": "read", "type": "text", "content": content, "ok": True})
                else:
                    print(content)
            else:
                saved = _read_image(file_path)
                if as_json:
                    print_json({"action": "read", "type": "image", "file": saved, "ok": True})
                else:
                    print(f"Saved image to {saved}")

        elif action == "write":
            if content_type == "text":
                if not text:
                    raise SteerError("Text argument required for write")
                _write_text(text)
                if as_json:
                    print_json({"action": "write", "type": "text", "ok": True})
                else:
                    print(f"Copied to clipboard")
            else:
                if not file_path:
                    raise SteerError("--file required for image write")
                _write_image(file_path)
                if as_json:
                    print_json({"action": "write", "type": "image", "ok": True})
                else:
                    print(f"Copied image to clipboard")

    except SteerError as e:
        print_error(str(e))
        sys.exit(1)

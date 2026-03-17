"""Steer CLI — Ubuntu automation for AI agents. Eyes and hands on your Linux device."""

import sys
from pathlib import Path

# Add the app directory to path so modules can be imported
sys.path.insert(0, str(Path(__file__).parent))

import click

from commands.see import see
from commands.click_cmd import click_cmd
from commands.type_cmd import type_cmd
from commands.hotkey import hotkey
from commands.scroll import scroll
from commands.drag import drag
from commands.apps import apps
from commands.screens import screens
from commands.window import window
from commands.ocr import ocr
from commands.focus import focus
from commands.find import find
from commands.clipboard import clipboard
from commands.wait import wait


@click.group()
@click.version_option(version="0.2.0", prog_name="steer")
def cli():
    """Ubuntu automation CLI for AI agents. Eyes and hands on your Linux device."""
    pass


cli.add_command(see)
cli.add_command(click_cmd, name="click")
cli.add_command(type_cmd, name="type")
cli.add_command(hotkey)
cli.add_command(scroll)
cli.add_command(drag)
cli.add_command(apps)
cli.add_command(screens)
cli.add_command(window)
cli.add_command(ocr)
cli.add_command(focus)
cli.add_command(find)
cli.add_command(clipboard)
cli.add_command(wait)


if __name__ == "__main__":
    cli()

"""find — Search elements by text in latest snapshot."""

import sys

import click

from modules import element_store
from modules.errors import SteerError
from modules.output import print_json, print_error, format_element_row


@click.command()
@click.argument("query")
@click.option("--snapshot", default=None, help="Snapshot ID; default: latest")
@click.option("--exact", is_flag=True, default=False, help="Exact match only")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output JSON")
def find(query, snapshot, exact, as_json):
    """Search for UI elements by text in a snapshot."""
    try:
        if snapshot:
            snap_id = snapshot
            elements = element_store.load(snap_id)
        else:
            snap_id, elements = element_store.latest()

        q_lower = query.lower()
        matches = []

        for el in elements:
            label = (el.get("label") or "").lower()
            value = (el.get("value") or "").lower()

            if exact:
                if label == q_lower or value == q_lower:
                    matches.append(el)
            else:
                if q_lower in label or q_lower in value:
                    matches.append(el)

        if as_json:
            print_json({
                "snapshot": snap_id,
                "query": query,
                "count": len(matches),
                "matches": matches,
            })
        else:
            print(f"Snapshot: {snap_id}")
            print(f"Query: \"{query}\"")
            print(f"Matches: {len(matches)}")
            for el in matches:
                print(format_element_row(el))

    except SteerError as e:
        print_error(str(e))
        sys.exit(1)

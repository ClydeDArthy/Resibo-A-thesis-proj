"""Preferences that outlive a run, kept in a small JSON file beside the app."""

import json
import os

PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "settings.json")

DEFAULTS = {"theme": "Dark"}


def load():
    """Read the saved preferences, falling back to the defaults."""
    values = dict(DEFAULTS)
    try:
        with open(PATH, encoding="utf-8") as handle:
            saved = json.load(handle)
        if isinstance(saved, dict):
            values.update({k: v for k, v in saved.items() if k in DEFAULTS})
    except (OSError, ValueError):
        pass
    return values


def save(**changes):
    """Merge changes into the saved preferences."""
    values = load()
    values.update({k: v for k, v in changes.items() if k in DEFAULTS})
    try:
        with open(PATH, "w", encoding="utf-8") as handle:
            json.dump(values, handle, indent=2)
    except OSError:
        pass
    return values

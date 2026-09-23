"""Evidence files being taken in.

Hashing is real: each file is read in chunks from the render loop, so the
progress bar tracks actual work and a cancel genuinely stops it.
"""

import hashlib
import os

CHUNK = 2 * 1024 * 1024        # bytes read per frame, per file

# Each entry: name, path, size, read, sha (running), digest, state.
# state is one of: reading, done, error
FILES = []


def size_text(num):
    """Human-readable file size."""
    if num <= 0:
        return "0 B"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if num < 1024 or unit == "TB":
            return "{:.0f} {}".format(num, unit) if unit == "B" else "{:.2f} {}".format(num, unit)
        num /= 1024.0
    return "0 B"


def add(path):
    """Queue one file for hashing. Ignores duplicates."""
    path = os.path.abspath(path)
    if any(f["path"] == path for f in FILES):
        return None
    try:
        size = os.path.getsize(path)
    except OSError:
        return None
    entry = {
        "name": os.path.basename(path), "path": path, "size": size,
        "read": 0, "sha": hashlib.sha256(), "digest": "", "state": "reading",
        "handle": None,
    }
    FILES.append(entry)
    return entry


def remove(index):
    """Drop a file, closing it if it is still being read."""
    if 0 <= index < len(FILES):
        entry = FILES.pop(index)
        if entry["handle"]:
            try:
                entry["handle"].close()
            except OSError:
                pass


def clear():
    for i in range(len(FILES) - 1, -1, -1):
        remove(i)


def progress(entry):
    """0.0 to 1.0 for one file."""
    if entry["size"] <= 0:
        return 1.0
    return min(1.0, entry["read"] / entry["size"])


def totals():
    """Exhibit count and combined size of the files taken in so far."""
    return len(FILES), sum(f["size"] for f in FILES)


def all_done():
    return bool(FILES) and all(f["state"] == "done" for f in FILES)


def tick():
    """Read one chunk from every file still being hashed.

    Returns True if anything changed, so the caller can redraw.
    """
    changed = False
    for entry in FILES:
        if entry["state"] != "reading":
            continue
        changed = True
        try:
            if entry["handle"] is None:
                entry["handle"] = open(entry["path"], "rb")
            block = entry["handle"].read(CHUNK)
            if block:
                entry["sha"].update(block)
                entry["read"] += len(block)
            else:
                entry["handle"].close()
                entry["handle"] = None
                entry["digest"] = entry["sha"].hexdigest()
                entry["read"] = entry["size"]
                entry["state"] = "done"
        except OSError:
            entry["state"] = "error"
            entry["handle"] = None
    return changed

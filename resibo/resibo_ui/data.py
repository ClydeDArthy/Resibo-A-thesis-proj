"""Sample case data for the RESIBO front-end demo.

Values mirror the approved UI mockups. Replace these dictionaries with the
real pipeline output when the back-end modules are wired in.
"""

EXAMINER = {
    "name": "M. E. Inocencio",
    "full_name": "Maria Edona I. Inocencio",
    "phone": "+639 - nowmber",
    "email": "einocencio@students.nu-manila.edu.ph",
}

VAULT = "/mnt/evidence_vault"
SEGMENT = "VLAN-310-FORENSIC-ISOLATED"

# --- Overview -------------------------------------------------------------
CASES = [
    {"examiner": "M. E. Inocencio", "number": "CASE-2026-09A", "place": "Warehouse B", "badge": "Active", "tone": "green",
     "name": "Alleged theft - Warehouse B", "opened": "2026-08-27", "exhibits": 3,
     "flags": 10, "chain": "verified", "status": "Processing", "done": 7},
    {"examiner": "A. D. S. Garcia", "number": "CASE-2026-07B", "place": "Brgy. 123 main gate", "badge": "Open", "tone": "blue",
     "name": "Snatching - Brgy. 123 gate", "opened": "2026-07-19", "exhibits": 2,
     "flags": 1, "chain": "verified", "status": "Awaiting review", "done": 2},
    {"examiner": "J. M. D. Marisga", "number": "CASE-2026-05C", "place": "Ortigas Ave.", "badge": "Open", "tone": "blue",
     "name": "Hit and run - Ortigas Ave.", "opened": "2026-05-04", "exhibits": 5,
     "flags": 0, "chain": "verified", "status": "Intake only", "done": 1},
    {"examiner": "R. C. Osorio", "number": "CASE-2025-11A", "place": "Perimeter cam", "badge": "Exported", "tone": "green",
     "name": "Trespassing - perimeter cam", "opened": "2025-11-12", "exhibits": 1,
     "flags": 2, "chain": "verified", "status": "Closed", "done": 7},
]

ACTIVE_CASE = CASES[0]

# Seven pipeline stages shown on the case overview, with the note each
# stage leaves once it has finished.
PROGRESS = [
    ("Evidence intake", "files hashed and sealed", "amber_if_flagged"),
    ("Stream check", "1 timestamp gap", "flag"),
    ("Detection and tracking", "4 people found", ""),
    ("Face enhancement", "running", ""),
    ("Gait analysis", "waiting", ""),
    ("Identity resolution", "waiting", ""),
    ("Report", "waiting", ""),
]


def progress_for(case):
    """Stage rows for one case: done, running, then queued."""
    done = case["done"]
    rows = []
    for i, (name, note, kind) in enumerate(PROGRESS):
        if i < done:
            badge, tone = "Done", ("amber" if kind == "flag" else "green")
            sub = note
        elif i == done:
            badge, tone, sub = "Running", "blue", "running"
        else:
            badge, tone, sub = "Queued", "gray", "waiting"
        rows.append((name, sub, badge, tone))
    return rows



# --- Appearance ------------------------------------------------------------
# Each tracked person is drawn differently, so no two samples look alike.
# build/height scale the figure; the colours drive the drawn crops.
LOOKS = {
    "person 5":  {"skin": (168, 124, 96), "hair": (44, 32, 26), "shirt": (78, 92, 104),
                  "build": 1.00, "height": 1.00, "hair_style": "short"},
    "person 7":  {"skin": (140, 100, 78), "hair": (28, 22, 20), "shirt": (92, 76, 68),
                  "build": 1.12, "height": 1.06, "hair_style": "cap"},
    "person 11": {"skin": (198, 160, 130), "hair": (96, 72, 40), "shirt": (66, 84, 78),
                  "build": 0.84, "height": 0.88, "hair_style": "long"},
    "person 12": {"skin": (122, 88, 66), "hair": (20, 18, 18), "shirt": (104, 88, 96),
                  "build": 0.92, "height": 0.94, "hair_style": "short"},
    "person 14": {"skin": (186, 146, 116), "hair": (70, 52, 34), "shirt": (72, 80, 96),
                  "build": 1.05, "height": 1.02, "hair_style": "cap"},
    "person 15": {"skin": (152, 112, 86), "hair": (36, 28, 22), "shirt": (88, 96, 86),
                  "build": 0.90, "height": 0.92, "hair_style": "long"},
    "person 18": {"skin": (176, 136, 104), "hair": (52, 38, 28), "shirt": (70, 74, 92),
                  "build": 1.08, "height": 1.04, "hair_style": "short"},
    "person 21": {"skin": (132, 96, 74), "hair": (24, 20, 18), "shirt": (96, 84, 76),
                  "build": 0.96, "height": 0.98, "hair_style": "cap"},
}

DEFAULT_LOOK = LOOKS["person 5"]


def look(person):
    """Appearance for a person, falling back to a neutral one."""
    return LOOKS.get(person, DEFAULT_LOOK)


# --- Evidence intake ------------------------------------------------------
EVIDENCE = [
    ("EXH-001", "CAM04_2026-08-14_0300.mp4", "1.42 GB", "a91c3f5b8e2d7104...", "Sealed"),
    ("EXH-002", "CAM04_2026-08-14_0400.mp4", "0.86 GB", "7c2e91b4f0a6d358...", "Sealed"),
    ("EXH-003", "camera_export_log.txt", "12 KB", "3f80a1c95d7be264...", "Sealed"),
]
EVIDENCE_SUMMARY = [
    ("Exhibits", "3", "text"), ("Total size", "2.28 GB", "text"),
    ("Hash", "SHA-256", "text"), ("Sealed at", "08:45:02", "green"),
]

# --- Workflow steps shown on the case progress panel ----------------------
# Each step opens a screen and carries the flags that stage raised.
STEPS = [
    {"label": "Evidence intake", "screen": "Evidence", "note": "files hashed and sealed",
     "flags": []},
    {"label": "Stream check", "screen": "Working copy", "note": "integrity of the recording",
     "flags": [("1 timestamp gap at 00:02:41", "amber"),
               ("frame rate 30 stated, 29.94 actual", "amber")]},
    {"label": "Clips received", "screen": "Clips", "note": "4 segments carved and hashed",
     "flags": []},
    {"label": "Detection and tracking", "screen": "Person detection",
     "note": "4 people found",
     "flags": [("person 7 - ID may have swapped", "amber"),
               ("person 11 - low confidence 0.64", "amber"),
               ("person 12 - too short, 41 frames", "amber")]},
    {"label": "Face enhancement", "screen": "Face enhancement",
     "note": "RetinaFace, EIPNet, AdaFace",
     "flags": [("person 11 - 0.52, below the 0.60 pass mark", "amber")]},
    {"label": "Gait analysis", "screen": "Person detection",
     "note": "walk patterns built, saved per identity",
     "flags": [("person 7 - left vs right 0.17 apart", "amber")]},
    {"label": "Walking analysis", "screen": "Walking", "note": "2 of 4 usable",
     "flags": [("person 7 - usable with caution, carrying a bag", "amber"),
               ("person 11 - not usable, mostly hidden", "amber"),
               ("person 12 - not usable, clip too short", "amber")]},
    {"label": "Report and audit", "screen": "History", "note": "chain of 5,318 records",
     "flags": [("report not generated yet", "gray")]},
]


def step_state(step_index, case):
    """Badge and tone for one step, given how far the case has run."""
    done = case["done"]
    if step_index < done:
        flags = STEPS[step_index]["flags"]
        if flags:
            return "{} flag{}".format(len(flags), "" if len(flags) == 1 else "s"), "amber"
        return "Done", "green"
    if step_index == done:
        return "Running", "blue"
    return "Queued", "gray"


# --- Clips received -------------------------------------------------------
CLIPS = [
    {"id": "SEG-01", "event": "event 1", "badge": "Verified", "tone": "green",
     "span": "1:11 - 1:49", "length": "37.9 s", "hash": "f1c6853bd204e7f9...",
     "at": "00:00:14", "total": "00:00:38"},
    {"id": "SEG-02", "event": "event 2", "badge": "Verified", "tone": "green",
     "span": "2:24 - 3:04", "length": "39.5 s", "hash": "c73a19e8bd5024fa...",
     "at": "00:00:21", "total": "00:00:40"},
    {"id": "SEG-04", "event": "event 3", "badge": "Open", "tone": "blue",
     "span": "3:28 - 3:45", "length": "16.5 s", "hash": "9ab4c1d7e0f38256...",
     "at": "00:00:06", "total": "00:00:17"},
    {"id": "SEG-05", "event": "event 4", "badge": "Verified", "tone": "green",
     "span": "3:52 - 3:53", "length": "1.4 s", "hash": "24e7f0a3b6c9d2e5...",
     "at": "00:00:00", "total": "00:00:01"},
]
CLIPS_SUMMARY = "4 clips - 214 MB"

# --- Working copy ---------------------------------------------------------
COPY_STEPS = [
    ("Original locked", "Done", "green"),
    ("Original hashed", "Done", "green"),
    ("Details read", "Done", "green"),
    ("Copy made", "Done", "green"),
    ("Copy hashed", "Done", "green"),
    ("Hashes compared", "Match", "green"),
]

COPY_HASHES = [
    ("Original", "a91c3f5b8e2d7104...", ("Sealed", "green", True)),
    ("Working copy", "a91c3f5b8e2d7104...", ("Match", "green", True)),
]

VIDEO_DETAILS = [
    ("Length", "4 min 23 s", "text"),
    ("Frames", "7,905", "text"),
    ("Frame rate", "30 stated, 29.94 actual", "amber"),
    ("Format", "MP4 - H.264 - 1920 x 1080", "text"),
]

COPY_RECORD = {
    "id": "COPY-0001",
    "converted": "no",
    "reason": "already MP4",
    "frames": "7,905",
    "result": "success",
}

# --- People (detection and tracking) --------------------------------------
PEOPLE_STEPS = [
    ("Detection", "YOLO11", "Done", "green", 1.0),
    ("Tracking", "ByteTrack", "Done", "green", 1.0),
    ("Landmarking" + chr(10) + "and Face alignment", "RetinaFace",
     "Review", "amber", 0.78),
    ("Saving Outputs", "vault write", "Saving", "green", 0.92),
]

PEOPLE = [
    {"id": "person 5", "frames": "892 frames", "conf": "0.91", "conf_tone": "green",
     "state": "OK", "state_tone": "green"},
    {"id": "person 7", "frames": "712 frames", "conf": "0.87", "conf_tone": "green",
     "state": "ID may have swapped", "state_tone": "amber"},
    {"id": "person 11", "frames": "148 frames", "conf": "0.64", "conf_tone": "amber",
     "state": "Low confidence", "state_tone": "amber"},
    {"id": "person 12", "frames": "41 frames", "conf": "0.82", "conf_tone": "green",
     "state": "Too short", "state_tone": "amber"},
]

# Presence lanes: (start, end, tone) as fractions of the clip length.
PEOPLE_TRACKS = {
    "person 5": [(0.02, 0.32, "green"), (0.36, 0.55, "green")],
    "person 7": [(0.28, 0.44, "green"), (0.53, 0.70, "green")],
    "person 11": [(0.55, 0.65, "amber")],
    "person 12": [(0.82, 0.86, "amber")],
}

SAVED_PERSONS = [
    ("person 5", "clean + annotated", "green"),
    ("person 7", "clean + annotated", "green"),
    ("person 11", "clean + annotated", "amber"),
    ("person 12", "clean + annotated", "amber"),
]


# --- Saved identity folders ------------------------------------------------
# Detection saves one folder per identity; each holds raw and enhanced crops.
IDENTITIES = [
    ("ID 1234", "green", "person 5"),
    ("ID 4321", "green", "person 7"),
    ("ID 3214", "amber", "person 11"),
    ("ID 0617", "amber", "person 12"),
]

# (frame, enhanced) - every folder holds the same sample set.
FOLDER_ITEMS = [
    ("2884", False), ("2884", True),
    ("3120", False), ("3120", True),
    ("3355", False), ("3355", True),
]


def identity_for(person):
    """The identity assigned to a tracked person, if any."""
    for ident, _tone, key in IDENTITIES:
        if key == person:
            return ident
    return person


def folder_meta(ident, kind, frame, enhanced):
    """Rows shown beside an image in the preview window."""
    if kind == "gait":
        return [("Identity", ident, "text"),
                ("Frame", frame, "text"),
                ("Kind", "annotated" if enhanced else "clean", "green" if enhanced else "dim"),
                ("Source", "person box folder", "text"),
                ("Model", "MediaPipe Pose" if enhanced else "YOLO11", "text")]
    return [("Identity", ident, "text"),
            ("Frame", frame, "text"),
            ("Kind", "enhanced" if enhanced else "raw", "green" if enhanced else "dim"),
            ("Size", "112 x 112" if enhanced else "64 x 64", "text"),
            ("Model", "EIPNet" if enhanced else "YOLO11-face", "text")]


# --- Faces ----------------------------------------------------------------
FACE_STEPS = [
    ("BBox", "", "Done", "green", 1.0),
    ("Landmarks", "", "Done", "green", 1.0),
    ("Standard Crop", "", "Processing", "amber", 0.74),
    ("Enhancement", "", "Running", "blue", 0.48),
]

# (letter, caption, sub, blurred, selected, landmarks)
# One tile per stage: (caption, sub, blurred, bbox, landmarks)
FACE_TILES = [
    ("BBox", "", True, True, False),
    ("Landmarks", "", True, False, True),
    ("Standard crop", "112 x 112 . clean + annotated", True, False, False),
    ("Enhanced", "", False, False, False),
]

# The Faces screen refers to people by their assigned identity number.
FACE_PERSONS = [
    ("ID 1234", "clean + annotated", "green", "person 5"),
    ("ID 4321", "clean + annotated", "green", "person 7"),
    ("ID 3214", "clean + annotated", "amber", "person 11"),
    ("ID 0617", "clean + annotated", "amber", "person 12"),
]

FACE_FRAMES = ["1402", "2884", "3910", "4177"]

# --- Gait -----------------------------------------------------------------
GAIT_PEOPLE = [
    ("person 5", "892 f"), ("person 7", "712 f"), ("person 11", "148 f"),
    ("person 12", "41 f"), ("person 14", "233 f"), ("person 15", "96 f"),
    ("person 18", "410 f"), ("person 21", "77 f"),
]

# (label, caption, score) - before/after pairs from the sharpening step.
FACE_OUTPUT = [
    ("Before", "frame 2884", ""), ("After", "frame 2884", "0.74"),
    ("Before", "frame 3120", ""), ("After", "frame 3120", "0.71"),
    ("Before", "frame 3355", ""), ("After", "frame 3355", "0.68"),
]

MATCH_SUMMARY = {
    "person 5": [("Before", "0.72", "unsharpened crop", "text"),
                 ("After", "0.81", "sharpened crop", "green"),
                 ("Pass mark", "0.60", "to count as a match", "text")],
    "person 7": [("Before", "0.69", "unsharpened crop", "text"),
                 ("After", "0.74", "sharpened crop", "green"),
                 ("Pass mark", "0.60", "to count as a match", "text")],
    "person 11": [("Before", "0.41", "unsharpened crop", "text"),
                  ("After", "0.52", "sharpened crop", "amber"),
                  ("Pass mark", "0.60", "to count as a match", "text")],
}
MATCHED_IDENTITY = {"person 5": "Identity 2", "person 7": "Identity 6",
                    "person 11": "no match", "person 12": "no match"}


def match_summary(person):
    """Face-score tiles for a person, or the below-threshold set."""
    return MATCH_SUMMARY.get(person, MATCH_SUMMARY["person 11"])

# --- Walking (gait detail) ------------------------------------------------
WALK_RESULTS = [
    ("person 5", "clear view", "Usable", "green"),
    ("person 7", "carrying a bag", "Caution", "amber"),
    ("person 11", "mostly hidden", "No", "amber"),
    ("person 12", "too short", "No", "amber"),
]

PERSON_FOLDERS = [
    ("person 5", "892 clean - 892 annotated", "green"),
    ("person 7", "712 clean - 712 annotated", "green"),
    ("person 11", "148 clean - 148 annotated", "amber"),
    ("person 12", "41 clean - 41 annotated", "amber"),
]

WALK_STAGES = [
    ("a", "Person box", "from tracking"),
    ("b", "Person cut out", "clean image"),
    ("c", "Body points", "joints marked"),
    ("d", "Walk cycles", "heel to heel"),
    ("e", "Walk pattern", "built"),
]

WALK_TABLE = [
    ("person 5", "6 complete", "112 steps/min", ("0.08 apart", "green"), ("Yes", "green", True)),
    ("person 7", "4 complete", "108 steps/min", ("0.17 apart", "amber"), ("With caution", "amber", True)),
    ("person 11", ("1 partial", "amber"), "-", "-", ("No", "amber", True)),
    ("person 12", ("0", "amber"), "-", "-", ("No", "amber", True)),
]

WALK_DETAILS = {
    "person 5": {
        "id": "GAIT-0005", "warn": None,
        "input": [("From", "person box folder", "text"), ("Clean images", "892", "text"),
                  ("Annotated", "892", "text")],
        "measured": [("Walk cycles", "6", "text"), ("Cadence", "112 steps/min", "text"),
                     ("Stance : swing", "61 : 39", "text"), ("Double support", "10%", "text"),
                     ("Left vs right", "0.08 apart", "green")],
        "conditions": [("View angle", "about 15 deg oblique", "text"), ("Carrying", "none", "text"),
                       ("Cover", "clear view", "green"), ("Usable", "yes", "green")],
    },
    "person 7": {
        "id": "GAIT-0007",
        "warn": ("Bag and partial cover",
                 "The pattern was still built, but these conditions are recorded "
                 "next to any comparison."),
        "input": [("From", "person box folder", "text"), ("Clean images", "712", "text"),
                  ("Annotated", "712", "text")],
        "measured": [("Walk cycles", "4", "text"), ("Cadence", "108 steps/min", "text"),
                     ("Stance : swing", "62 : 38", "text"), ("Double support", "11%", "text"),
                     ("Left vs right", "0.17 apart", "amber")],
        "conditions": [("View angle", "about 40 deg oblique", "amber"),
                       ("Carrying", "bag", "amber"), ("Cover", "partly hidden", "amber"),
                       ("Usable", "with caution", "amber")],
    },
    "person 11": {
        "id": "GAIT-0011",
        "warn": ("Mostly hidden",
                 "The person is behind a rack for most of the clip, so no full walk "
                 "cycle could be measured."),
        "input": [("From", "person box folder", "text"), ("Clean images", "148", "text"),
                  ("Annotated", "148", "text")],
        "measured": [("Walk cycles", "1 partial", "amber"), ("Cadence", "-", "text"),
                     ("Stance : swing", "-", "text"), ("Double support", "-", "text"),
                     ("Left vs right", "-", "text")],
        "conditions": [("View angle", "about 70 deg oblique", "amber"),
                       ("Carrying", "unknown", "amber"), ("Cover", "mostly hidden", "amber"),
                       ("Usable", "no", "amber")],
    },
    "person 12": {
        "id": "GAIT-0012",
        "warn": ("Clip too short",
                 "41 frames is under one walk cycle at this frame rate, so no "
                 "pattern was built."),
        "input": [("From", "person box folder", "text"), ("Clean images", "41", "text"),
                  ("Annotated", "41", "text")],
        "measured": [("Walk cycles", "0", "amber"), ("Cadence", "-", "text"),
                     ("Stance : swing", "-", "text"), ("Double support", "-", "text"),
                     ("Left vs right", "-", "text")],
        "conditions": [("View angle", "about 25 deg oblique", "text"),
                       ("Carrying", "none", "text"), ("Cover", "clear view", "green"),
                       ("Usable", "no", "amber")],
    },
}

WALK_NOTES = [
    ("Only two moments can be seen from the video",
     "Clinical gait charts split one cycle into eight events. From body points on CCTV only "
     "heel down and toe off are reliable, so the toolkit reports cycle count, pace, "
     "stance-to-swing split and left-right difference, and nothing finer.", "blue"),
    ("Walking is supporting evidence only",
     "Bags, clothing and camera angle all change how someone walks. Gait can back up or "
     "question a face result, but never stands alone.", "amber"),
]

# --- History (audit trail) ------------------------------------------------
HISTORY_STAGES = [
    ("Case intake", "2 records", "OK", "green"),
    ("Evidence intake", "4 records", "OK", "green"),
    ("Working copy", "4 records", "OK", "green"),
    ("Stream check", "6 records", "1 flag", "amber"),
    ("Clips received", "8 records", "OK", "green"),
    ("People", "118 records", "2 flags", "amber"),
    ("Faces", "4,912 records", "1 flag", "amber"),
    ("Walking", "249 records", "1 flag", "amber"),
    ("Identity", "6 records", "OK", "green"),
    ("Report", "0 records", "Not ready", "gray"),
]

# Which workflow step writes each stage, so a stage only appears once the
# case has actually reached it.
STAGE_STEP = {
    "Case intake": 0, "Evidence intake": 0, "Working copy": 1, "Stream check": 1,
    "Clips received": 2, "People": 3, "Faces": 4, "Walking": 6,
    "Identity": 7, "Report": 7,
}

# (record, time, stage, what happened, linked, flagged)
HISTORY_RECORDS = [
    ("IDR-0007", "09:58:02", "Identity", "results combined", "Yes", False),
    ("GAIT-0007", "09:52:41", "Walking", "walk pattern built", "Yes", False),
    ("GAIT-0005", "09:50:18", "Walking", "usable with caution", "Yes", True),
    ("MATCH-4823", "09:41:09", "Faces", "compared to known people", "Yes", False),
    ("ENH-004821", "09:41:07", "Faces", "face sharpened", "Yes", False),
    ("FDET-004820", "09:39:52", "Faces", "below the pass mark", "Yes", True),
    ("TRK-0007", "09:22:04", "People", "ID may have swapped", "Yes", True),
    ("TRK-0005", "09:21:40", "People", "person followed", "Yes", False),
    ("CLIP-0004", "09:17:22", "Clips received", "hash checked on arrival", "Yes", False),
    ("PTSD-0001", "08:51:20", "Stream check", "gap found in the video", "Yes", True),
    ("COPY-0001", "08:47:33", "Working copy", "copy matches original", "Yes", False),
    ("META-0001", "08:46:10", "Working copy", "video details read", "Yes", False),
    ("EVD-0001", "08:45:02", "Evidence intake", "files hashed and sealed", "Yes", False),
    ("INIT-0001", "08:44:01", "Case intake", "case started", "First", False),
]


def records_for(case):
    """Audit records this case has actually written, newest first."""
    done = case["done"]
    return [(i, r) for i, r in enumerate(HISTORY_RECORDS)
            if STAGE_STEP.get(r[2], 99) < done]


def stages_for(case):
    """Stage rows with the counts this case really holds."""
    rows = []
    for name, _count, _badge, _tone in HISTORY_STAGES:
        step = STAGE_STEP.get(name, 99)
        mine = [r for _i, r in records_for(case) if r[2] == name]
        flags = sum(1 for r in mine if r[5])
        if step >= case["done"]:
            rows.append((name, "not run yet", "Queued", "gray"))
        elif flags:
            rows.append((name, "{} records".format(len(mine)),
                         "{} flag{}".format(flags, "" if flags == 1 else "s"), "amber"))
        else:
            rows.append((name, "{} records".format(len(mine)), "OK", "green"))
    return rows

def history_detail(index):
    """Build the right-hand detail for one audit record."""
    rec, time, stage, what, linked, flagged = HISTORY_RECORDS[index]
    return {
        "id": rec,
        "sub": what,
        "record": [("Record", rec, "text"),
                   ("Number", "{:,} of 5,318".format(5318 - index), "text"),
                   ("Stage", stage, "text"),
                   ("Time", time + ".554", "text"),
                   ("Flagged", "yes" if flagged else "no",
                    "amber" if flagged else "dim")],
        "chain": [("Hash before", "b2e6d0f4a8c2...", "dim"),
                  ("This hash", "b5c6d7e8f9a0...", "dim"),
                  ("Linked", "yes" if linked == "Yes" else "first", "green"),
                  ("Checked", "09:59", "green")],
    }


def ankle_waveform(samples=260, cycles=4.0, phase=0.0, jitter=0.06):
    """Synthetic left/right ankle-height curve used by the gait charts."""
    import math
    import random

    rng = random.Random(7 if phase == 0 else 13)
    xs, ys = [], []
    for i in range(samples):
        t = i / (samples - 1)
        base = math.sin(2 * math.pi * cycles * t + phase)
        xs.append(t * 8.4)                               # seconds on the x axis
        ys.append(base + rng.uniform(-jitter, jitter))
    return xs, ys


# Heel-down markers drawn as vertical lines on the gait charts.
HEEL_STRIKES = [1.05, 3.15, 5.25, 7.30]

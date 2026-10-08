"""Live face stage UI. It never presents seeded face results as live output."""
import dearpygui.dearpygui as dpg
from .. import layout, live, state, theme as th, widgets as w

TITLE="Face enhancement"; CRUMB=("CASE-2026-09A","Face enhancement"); ACTION=None

def build():
    with dpg.group(horizontal=True):
        _left()
        _main()
        _right()

def refresh_live():
    for tag, fn in (("fc_main", _fill_main), ("fc_right", _fill_right)):
        if dpg.does_item_exist(tag): state.rebuild(tag, fn)

def _left():
    with dpg.child_window(width=300,border=True) as p:
        w.title("Face pipeline"); w.spacer(8); dpg.add_separator(); w.spacer(10)
        snap=live.snapshot()
        for name,key in (("Face detector","face"),("FR / OSDFace + AdaFace","face")):
            w.kv_row(name, snap["pipelines"].get(key,"idle"), "green" if snap["pipelines"].get(key) in ("ready","running","completed") else "amber")
        w.spacer(12)
        w.note("Live source","Face results come from the current OBJ track and the configured face/FR runtime. Seeded reference crops are not shown.","amber",wrap=260)
    dpg.bind_item_theme(p,th.T["panel"])

def _main():
    with dpg.child_window(width=-430,border=True) as p:
        with dpg.group(tag="fc_main"): _fill_main()
    dpg.bind_item_theme(p,th.T["pane"])

def _fill_main():
    snap=live.snapshot()
    w.title("Live face results","h1"); w.mono("same master_id and frame clock as OBJ","dim"); w.spacer(10)
    rows=[]
    for t in snap["tracks"]:
        f=t.get("face") or {}
        rows.append(("master_id "+str(t["master_id"]),t.get("frame_index","-"),f.get("detector","waiting"),f.get("faces",0),f.get("candidate") or "-",f.get("score") if f.get("score") is not None else "-"))
    if rows: w.table(["Track","Frame","Detector","Faces","Candidate","Score"],rows,weights=[1.2,.8,1,0.6,1.4,1])
    else: w.note("Waiting for face output","Start a case with an accessible video. The live face detector will follow OBJ tracks.","amber",wrap=500)

def _right():
    with dpg.child_window(width=-1,border=True) as p:
        with dpg.group(tag="fc_right"): _fill_right()
    dpg.bind_item_theme(p,th.T["panel"])

def _fill_right():
    w.title("Current tracks")
    for t in live.tracks():
        f=t.get("face") or {}
        w.kv_row("master_id "+str(t["master_id"]), f.get("candidate") or "No FR candidate", "green" if f.get("candidate") else "amber")

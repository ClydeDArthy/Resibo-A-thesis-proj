"""Live case progress."""
import dearpygui.dearpygui as dpg
from .. import data, layout, live, state, theme as th, widgets as w
TITLE="Progress"; CRUMB=("CASE-2026-09A","Progress"); ACTION=None
_open_screen=[None]; _expanded={"step":None}
def set_opener(fn): _open_screen[0]=fn
def build():
    with dpg.group(horizontal=True): _live(); _details()
def refresh(): refresh_live()
def refresh_live():
    if dpg.does_item_exist("pg_live"): state.rebuild("pg_live",_fill_live)
def _live():
    with dpg.child_window(width=-360,border=True) as p:
        with dpg.group(tag="pg_live"): _fill_live()
    dpg.bind_item_theme(p,th.T["pane"])
def _fill_live():
    w.title(data.CASES[state.SEL["case"]]["name"],"h1")
    w.mono("Live model pipeline","dim"); w.spacer(10); dpg.add_separator(); w.spacer(12)
    snap=live.snapshot()
    w.table(["Stage","State"],[
        ("YOLO11 + BoT-SORT",snap["pipelines"]["obj"]),
        ("Face / OSDFace + AdaFace",snap["pipelines"]["face"]),
        ("Gait / GaitBase",snap["pipelines"]["gait"]),
        ("RESIBO",snap["pipelines"]["resibo"]),
    ],weights=[1.7,1])
    w.spacer(16)
    w.section("Tracked people","same live master_id state used by every stage")
    for t in snap["tracks"]:
        f=t.get("face") or {}; g=t.get("gait") or {}; r=t.get("resolution")
        w.kv_row("master_id "+str(t["master_id"]),
                 "face={} | gait={} | RESIBO={}".format(f.get("candidate") or "-",g.get("status","waiting"),getattr(r,"state","waiting") if r else "waiting"))
def _details():
    with dpg.child_window(width=-1,border=True) as p:
        w.title("Case details"); w.kv_row("Number",data.CASES[state.SEL["case"]]["number"]); w.kv_row("Chain",data.CASES[state.SEL["case"]]["chain"],"green")
    dpg.bind_item_theme(p,th.T["panel"])

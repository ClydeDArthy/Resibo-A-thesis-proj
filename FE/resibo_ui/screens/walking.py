"""Live gait and RESIBO state UI."""
import dearpygui.dearpygui as dpg
from .. import layout, live, state, theme as th, widgets as w

TITLE="Walking"; CRUMB=("CASE-2026-09A","Walking"); ACTION=None

def build():
    with dpg.group(horizontal=True):
        _left(); _main(); _right()

def refresh_live():
    for tag,fn in (("wk_main",_fill_main),("wk_right",_fill_right)):
        if dpg.does_item_exist(tag): state.rebuild(tag,fn)

def _left():
    with dpg.child_window(width=300,border=True) as p:
        w.title("Live gait")
        snap=live.snapshot()
        w.kv_row("Gait stage",snap["pipelines"].get("gait","idle"),"green" if snap["pipelines"].get("gait") in ("ready","running","completed") else "amber")
        w.kv_row("RESIBO",snap["pipelines"].get("resibo","idle"),"green" if snap["pipelines"].get("resibo") in ("ready","running","completed") else "amber")
        w.spacer(12)
        w.note("No fabricated gait","A track remains waiting until a real silhouette and GaitBase embedding are available.","amber",wrap=260)
    dpg.bind_item_theme(p,th.T["panel"])

def _main():
    with dpg.child_window(width=-430,border=True) as p:
        with dpg.group(tag="wk_main"): _fill_main()
    dpg.bind_item_theme(p,th.T["pane"])

def _fill_main():
    w.title("Walking analysis","h1"); w.mono("OBJ → silhouette → GaitBase → RESIBO","dim"); w.spacer(10)
    rows=[]
    for t in live.tracks():
        g=t.get("gait") or {}; r=t.get("resolution")
        rows.append(("master_id "+str(t["master_id"]),g.get("frame_count",0),g.get("status","waiting"),
                     "ready" if g.get("embedding_ready") else "no",
                     getattr(r,"state","-") if r else "-",getattr(r,"candidate_id","-") if r else "-"))
    if rows: w.table(["Track","Frames","Gait","Embedding","RESIBO","Candidate"],rows,weights=[1.2,.7,1.3,1,1,1.4])
    else: w.note("Waiting for gait","Gait requires enough aligned silhouettes for the configured GaitBase window.","amber",wrap=500)

def _right():
    with dpg.child_window(width=-1,border=True) as p:
        with dpg.group(tag="wk_right"): _fill_right()
    dpg.bind_item_theme(p,th.T["panel"])

def _fill_right():
    w.title("Resolution")
    for t in live.tracks():
        r=t.get("resolution")
        if r is None:
            w.kv_row("master_id "+str(t["master_id"]),"Waiting","amber")
        else:
            w.kv_row("master_id "+str(t["master_id"]),r.state,"green" if r.state=="resolved" else "amber")
            w.kv_row("Candidate",r.candidate_id or "-")
            w.kv_row("Fused score","-" if r.fused_score is None else "{:.4f}".format(r.fused_score))

"""Gait chart: left and right ankle height over time, with heel-down markers."""

import dearpygui.dearpygui as dpg
from . import data, theme as th, widgets as w


def gait_chart(height=190, legend=True):
    """Two ankle-height curves plus amber lines where a heel lands."""
    with dpg.plot(height=height, width=-1, no_menus=True, no_box_select=True,
                  no_mouse_pos=True, no_title=True) as plot:
        if legend:
            dpg.add_plot_legend(location=dpg.mvPlot_Location_SouthWest, outside=False)
        x_axis = dpg.add_plot_axis(dpg.mvXAxis, no_gridlines=True, no_tick_marks=True)
        y_axis = dpg.add_plot_axis(dpg.mvYAxis, no_gridlines=True, no_tick_marks=True,
                                   no_tick_labels=True)

        lx, ly = data.ankle_waveform(phase=0.0)
        rx, ry = data.ankle_waveform(phase=3.14159)
        left = dpg.add_line_series(lx, ly, label="left ankle", parent=y_axis)
        right = dpg.add_line_series(rx, ry, label="right ankle", parent=y_axis)
        marks = dpg.add_inf_line_series(data.HEEL_STRIKES, parent=y_axis)

        dpg.bind_item_theme(left, th.line_theme(th.GREEN))
        dpg.bind_item_theme(right, th.line_theme(th.BLUE))
        dpg.bind_item_theme(marks, th.inf_line_theme(th.AMBER))

        dpg.set_axis_limits(x_axis, 0, 8.4)
        dpg.set_axis_limits(y_axis, -1.6, 1.6)
    return plot


def gait_chart_frame(caption="", hint=""):
    """Chart wrapped in a card with the high/low and duration labels."""
    with dpg.child_window(height=230, border=True, no_scrollbar=True, no_scroll_with_mouse=True) as box:
        if caption:
            with dpg.group(horizontal=True):
                w.text(caption, "text", "ui")
                if hint:
                    dpg.add_spacer(width=12)
                    w.mono(hint, "faint", small=True)
            w.spacer(6)
        with dpg.group(horizontal=True):
            with dpg.group():
                w.mono("high", "faint", small=True)
                dpg.add_spacer(height=120)
                w.mono("low", "faint", small=True)
            gait_chart(height=175 if caption else 195)
        with dpg.group(horizontal=True):
            dpg.add_spacer(width=40)
            w.mono("0.0 s", "faint", small=True)
            dpg.add_spacer(width=700)
            w.mono("8.4 s", "faint", small=True)
    dpg.bind_item_theme(box, th.T["card"])
    return box

"""Colors, fonts and reusable DearPyGui themes for the RESIBO interface."""

import os
import dearpygui.dearpygui as dpg

# --- Palettes --------------------------------------------------------------
# Every screen reads these module names, so switching palette and rebuilding
# the interface is enough to retheme the whole app.
PALETTES = {
    "Dark": {
        "BG_APP": (10, 12, 14), "BG_RAIL": (13, 16, 19), "BG_PANEL": (16, 20, 24),
        "BG_CARD": (23, 28, 33), "BG_CARD_HOVER": (30, 37, 43),
        "BG_CARD_SEL": (17, 34, 26), "BG_ROW_SEL": (20, 30, 28),
        "BORDER": (36, 43, 51), "BORDER_SEL": (46, 110, 78),
        "TEXT": (222, 228, 234), "TEXT_DIM": (124, 136, 148),
        "TEXT_FAINT": (88, 98, 108),
        "GREEN": (74, 222, 128), "GREEN_DEEP": (35, 134, 74),
        "AMBER": (214, 158, 46), "BLUE": (88, 166, 255), "RED": (229, 96, 96),
        "ACCENT": (74, 222, 128),
    },
    "Light": {
        "BG_APP": (242, 244, 247), "BG_RAIL": (228, 232, 237),
        "BG_PANEL": (250, 251, 252), "BG_CARD": (255, 255, 255),
        "BG_CARD_HOVER": (238, 242, 246), "BG_CARD_SEL": (222, 244, 231),
        "BG_ROW_SEL": (230, 243, 235),
        "BORDER": (205, 212, 220), "BORDER_SEL": (58, 158, 104),
        "TEXT": (28, 34, 40), "TEXT_DIM": (92, 102, 112),
        "TEXT_FAINT": (138, 148, 158),
        "GREEN": (24, 138, 76), "GREEN_DEEP": (32, 150, 86),
        "AMBER": (172, 116, 16), "BLUE": (28, 106, 200), "RED": (186, 52, 52),
        "ACCENT": (36, 170, 98),
    },
    "Pink": {
        "BG_APP": (26, 14, 22), "BG_RAIL": (32, 17, 27), "BG_PANEL": (36, 20, 31),
        "BG_CARD": (46, 26, 39), "BG_CARD_HOVER": (58, 33, 49),
        "BG_CARD_SEL": (62, 28, 50), "BG_ROW_SEL": (55, 26, 45),
        "BORDER": (72, 42, 60), "BORDER_SEL": (196, 96, 150),
        "TEXT": (244, 228, 238), "TEXT_DIM": (186, 142, 168),
        "TEXT_FAINT": (140, 102, 124),
        "GREEN": (246, 138, 190), "GREEN_DEEP": (168, 62, 118),
        "AMBER": (232, 158, 96), "BLUE": (158, 150, 244), "RED": (236, 96, 120),
        "ACCENT": (255, 176, 156),
    },
    "Dark blue": {
        "BG_APP": (10, 16, 32), "BG_RAIL": (13, 20, 40), "BG_PANEL": (16, 24, 46),
        "BG_CARD": (22, 33, 60), "BG_CARD_HOVER": (30, 44, 76),
        "BG_CARD_SEL": (20, 44, 74), "BG_ROW_SEL": (22, 40, 68),
        "BORDER": (38, 52, 84), "BORDER_SEL": (64, 128, 208),
        "TEXT": (222, 232, 246), "TEXT_DIM": (134, 152, 186),
        "TEXT_FAINT": (96, 114, 146),
        "GREEN": (92, 200, 208), "GREEN_DEEP": (32, 108, 136),
        "AMBER": (226, 168, 76), "BLUE": (104, 162, 255), "RED": (232, 104, 116),
        "ACCENT": (104, 162, 255),
    },
}

ORDER = ["Dark", "Light", "Pink", "Dark blue"]
CURRENT = ["Dark"]

# Names the rest of the app reads; set_palette() rewrites them.
BG_APP = BG_RAIL = BG_PANEL = BG_CARD = BG_CARD_HOVER = (0, 0, 0)
BG_CARD_SEL = BG_ROW_SEL = BORDER = BORDER_SEL = (0, 0, 0)
TEXT = TEXT_DIM = TEXT_FAINT = (0, 0, 0)
GREEN = GREEN_DEEP = AMBER = BLUE = RED = ACCENT = (0, 0, 0)


def set_palette(name):
    """Point the module colour names at one palette."""
    if name not in PALETTES:
        return
    CURRENT[0] = name
    globals().update(PALETTES[name])


set_palette("Dark")

# Filled at build_themes(); screens read them by name.
T = {}
F = {}

def _load_fonts():
    """Load Windows system fonts, falling back to the DearPyGui default."""
    ui = "C:/Windows/Fonts/segoeui.ttf"
    mono = "C:/Windows/Fonts/consola.ttf"
    with dpg.font_registry():
        if os.path.exists(ui):
            F["ui"] = dpg.add_font(ui, 16)
            F["ui_sm"] = dpg.add_font(ui, 14)
            F["h1"] = dpg.add_font(ui, 22)
            F["h2"] = dpg.add_font(ui, 18)
            F["big"] = dpg.add_font(ui, 28)
        if os.path.exists(mono):
            F["mono"] = dpg.add_font(mono, 15)
            F["mono_sm"] = dpg.add_font(mono, 13)
            F["mono_big"] = dpg.add_font(mono, 26)


def _theme(**kwargs):
    """Build a one-off theme from color/style keyword pairs."""
    with dpg.theme() as t:
        with dpg.theme_component(dpg.mvAll):
            for key, val in kwargs.items():
                if key.startswith("c_"):
                    dpg.add_theme_color(getattr(dpg, "mvThemeCol_" + key[2:]), val)
                else:
                    style = getattr(dpg, "mvStyleVar_" + key)
                    dpg.add_theme_style(style, *(val if isinstance(val, tuple) else (val,)))
    return t


def build_themes():
    """Build every shared theme for the current palette.

    Safe to call again after set_palette(); the fonts are only loaded once.
    """
    if not F:
        _load_fonts()

    # Global look: flat panels, thin borders, square-ish corners.
    with dpg.theme() as glob:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, BG_APP)
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, BG_APP)
            dpg.add_theme_color(dpg.mvThemeCol_PopupBg, BG_PANEL)
            dpg.add_theme_color(dpg.mvThemeCol_Border, BORDER)
            dpg.add_theme_color(dpg.mvThemeCol_Text, TEXT)
            dpg.add_theme_color(dpg.mvThemeCol_TextDisabled, TEXT_FAINT)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, BG_CARD)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, BG_CARD_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, BG_CARD_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_Button, BG_CARD)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, BG_CARD_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, BG_CARD_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_Header, BG_ROW_SEL)
            dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, BG_CARD_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_HeaderActive, BG_ROW_SEL)
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarBg, BG_APP)
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrab, (44, 52, 60))
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabHovered, (60, 70, 80))
            dpg.add_theme_color(dpg.mvThemeCol_Separator, BORDER)
            dpg.add_theme_color(dpg.mvThemeCol_TableBorderLight, BORDER)
            dpg.add_theme_color(dpg.mvThemeCol_TableBorderStrong, BORDER)
            dpg.add_theme_color(dpg.mvThemeCol_TableHeaderBg, BG_PANEL)
            dpg.add_theme_color(dpg.mvThemeCol_TableRowBg, BG_APP)
            dpg.add_theme_color(dpg.mvThemeCol_TableRowBgAlt, (14, 17, 20))
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrab, GREEN)
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrabActive, GREEN)
            dpg.add_theme_color(dpg.mvThemeCol_CheckMark, GREEN)
            dpg.add_theme_color(dpg.mvThemeCol_Tab, BG_APP)
            dpg.add_theme_color(dpg.mvThemeCol_TabHovered, BG_CARD)
            dpg.add_theme_color(dpg.mvThemeCol_TabActive, BG_APP)
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 0, 0)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 10, 7)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 8, 7)
            dpg.add_theme_style(dpg.mvStyleVar_CellPadding, 10, 10)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 4)
            dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_ChildBorderSize, 1)
            dpg.add_theme_style(dpg.mvStyleVar_ScrollbarSize, 10)
        with dpg.theme_component(dpg.mvPlot):
            dpg.add_theme_color(dpg.mvPlotCol_FrameBg, BG_PANEL, category=dpg.mvThemeCat_Plots)
            dpg.add_theme_color(dpg.mvPlotCol_PlotBg, BG_PANEL, category=dpg.mvThemeCat_Plots)
            dpg.add_theme_color(dpg.mvPlotCol_PlotBorder, BORDER, category=dpg.mvThemeCat_Plots)
            dpg.add_theme_color(dpg.mvPlotCol_AxisGrid, (30, 36, 42), category=dpg.mvThemeCat_Plots)
            dpg.add_theme_color(dpg.mvPlotCol_AxisText, TEXT_FAINT, category=dpg.mvThemeCat_Plots)
    T["global"] = glob

    # Panels and cards.
    T["panel"] = _theme(c_ChildBg=BG_PANEL, c_Border=BORDER, ChildRounding=0,
                        WindowPadding=(18, 14))
    T["pane"] = _theme(c_ChildBg=(0, 0, 0, 0), c_Border=(0, 0, 0, 0),
                       ChildRounding=0, WindowPadding=(22, 14))
    T["card"] = _theme(c_ChildBg=BG_CARD, c_Border=BORDER,
                       WindowPadding=(12, 9), ItemSpacing=(8, 3))
    T["card_sel"] = _theme(c_ChildBg=BG_CARD_SEL, c_Border=BORDER_SEL,
                           WindowPadding=(12, 9), ItemSpacing=(8, 3))
    T["card_flat"] = _theme(c_ChildBg=BG_PANEL, c_Border=BORDER,
                            WindowPadding=(14, 12), ItemSpacing=(8, 4))
    T["bare"] = _theme(c_ChildBg=(0, 0, 0, 0), c_Border=(0, 0, 0, 0), ChildBorderSize=0)

    # Text colors.
    for name, col in (("dim", TEXT_DIM), ("faint", TEXT_FAINT), ("green", GREEN),
                      ("amber", AMBER), ("blue", BLUE), ("red", RED), ("text", TEXT)):
        T["txt_" + name] = _theme(c_Text=col)

    # Status pills: a bordered button that is only read, never pressed.
    for name, col in (("green", GREEN), ("amber", AMBER), ("blue", BLUE), ("gray", TEXT_FAINT)):
        T["pill_" + name] = _theme(
            c_Text=col, c_Button=(0, 0, 0, 0), c_ButtonHovered=(0, 0, 0, 0),
            c_ButtonActive=(0, 0, 0, 0), c_Border=col,
            FrameBorderSize=1, FrameRounding=3, FramePadding=(8, 3))

    # Buttons.
    T["btn_primary"] = _theme(
        c_Text=(6, 18, 12), c_Button=GREEN_DEEP, c_ButtonHovered=(45, 160, 92),
        c_ButtonActive=GREEN_DEEP, FramePadding=(16, 8))
    T["btn_danger"] = _theme(
        c_Text=RED, c_Button=(38, 20, 20), c_ButtonHovered=(58, 26, 26),
        c_Border=RED, FrameBorderSize=1, FramePadding=(16, 8))
    T["btn_ghost"] = _theme(
        c_Text=TEXT, c_Button=BG_CARD, c_ButtonHovered=BG_CARD_HOVER,
        c_Border=BORDER, FrameBorderSize=1, FramePadding=(16, 8))
    T["nav"] = _theme(
        c_Button=BG_CARD, c_ButtonHovered=(48, 58, 68), c_ButtonActive=BG_CARD,
        FrameRounding=5)
    T["nav_active"] = _theme(
        c_Button=GREEN, c_ButtonHovered=GREEN, c_ButtonActive=GREEN, FrameRounding=5)

    # Borderless table used purely to right-align a row's trailing item.
    T["tight"] = _theme(CellPadding=(0, 0), ItemSpacing=(8, 3))

    # Rows that behave like list items.
    T["row_sel"] = _theme(c_ChildBg=BG_ROW_SEL, c_Border=(0, 0, 0, 0))

    # Progress bars, tinted per stage state.
    T["bar_green"] = _theme(c_PlotHistogram=GREEN, c_FrameBg=(30, 36, 42), FrameRounding=2)
    T["bar_amber"] = _theme(c_PlotHistogram=AMBER, c_FrameBg=(30, 36, 42), FrameRounding=2)
    T["bar_blue"] = _theme(c_PlotHistogram=BLUE, c_FrameBg=(30, 36, 42), FrameRounding=2)

    # Callout boxes used for analyst notes.
    T["note_blue"] = _theme(c_ChildBg=(15, 26, 38), c_Border=(32, 70, 110))
    T["note_amber"] = _theme(c_ChildBg=(32, 26, 12), c_Border=(96, 74, 22))

    dpg.bind_theme(glob)
    if "ui" in F:
        dpg.bind_font(F["ui"])


def line_theme(color):
    """Theme for a single plot line series."""
    with dpg.theme() as t:
        with dpg.theme_component(dpg.mvLineSeries):
            dpg.add_theme_color(dpg.mvPlotCol_Line, color, category=dpg.mvThemeCat_Plots)
            dpg.add_theme_style(dpg.mvPlotStyleVar_LineWeight, 1.6, category=dpg.mvThemeCat_Plots)
    return t


def inf_line_theme(color):
    """Theme for the vertical heel-down markers on gait charts."""
    with dpg.theme() as t:
        with dpg.theme_component(dpg.mvInfLineSeries):
            dpg.add_theme_color(dpg.mvPlotCol_Line, color, category=dpg.mvThemeCat_Plots)
            dpg.add_theme_style(dpg.mvPlotStyleVar_LineWeight, 1.2, category=dpg.mvThemeCat_Plots)
    return t

import os
import streamlit.components.v1 as components

_RELEASE = True

if _RELEASE:
    _component_func = components.declare_component(
        "battleship_board",
        path=os.path.join(os.path.dirname(__file__), "frontend")
    )
else:
    _component_func = components.declare_component(
        "battleship_board",
        url="http://localhost:3001"
    )


def battleship_board(
    board,
    mode="view",
    selected_ship_length=3,
    orientation="Horizontal",
    preview_anchor=None,
    key=None,
    height=520,
):
    return _component_func(
        board=board,
        mode=mode,
        selected_ship_length=selected_ship_length,
        orientation=orientation,
        preview_anchor=preview_anchor,
        key=key,
        default=None,
        height=height,
    )
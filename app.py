import streamlit as st
import streamlit.components.v1 as components
import numpy as np
import json

st.set_page_config(page_title="Deep Naval Search", layout="wide")

BOARD_SIZE = 10
COLS = list("ABCDEFGHIJ")

SHIPS = {
    "Portaaviones": 5,
    "Acorazado": 4,
    "Crucero": 3,
    "Submarino": 3,
    "Destructor": 2
}

def empty_board():
    return np.zeros((BOARD_SIZE, BOARD_SIZE), dtype=int)

def get_cells(row, col, length, orientation):
    cells = []
    if orientation == "Horizontal":
        for j in range(length):
            cells.append((row, col + j))
    else:
        for i in range(length):
            cells.append((row + i, col))
    return cells

def valid_placement(board, row, col, length, orientation):
    if orientation == "Horizontal" and col + length > BOARD_SIZE:
        return False
    if orientation == "Vertical" and row + length > BOARD_SIZE:
        return False

    for r, c in get_cells(row, col, length, orientation):
        if board[r, c] != 0:
            return False
    return True

def place_ship(board, ship_name, row, col, orientation):
    length = SHIPS[ship_name]
    if not valid_placement(board, row, col, length, orientation):
        return False

    for r, c in get_cells(row, col, length, orientation):
        board[r, c] = 1
    return True

def ensure_state():
    if "board" not in st.session_state:
        st.session_state.board = empty_board()
    if "selected_ship" not in st.session_state:
        st.session_state.selected_ship = "Portaaviones"
    if "orientation" not in st.session_state:
        st.session_state.orientation = "Horizontal"
    if "preview_anchor" not in st.session_state:
        st.session_state.preview_anchor = None

ensure_state()

def render_board_html(board, preview_anchor, ship_length, orientation, title):
    preview_cells = []
    preview_valid = True

    if preview_anchor is not None:
        preview_cells = get_cells(preview_anchor[0], preview_anchor[1], ship_length, orientation)
        preview_valid = valid_placement(board, preview_anchor[0], preview_anchor[1], ship_length, orientation)

    preview_set = {f"{r},{c}" for r, c in preview_cells}

    board_data = board.tolist()

    html = f"""
    <html>
    <head>
    <style>
      body {{
        margin: 0;
        font-family: Arial, sans-serif;
      }}
      .title {{
        font-size: 28px;
        font-weight: 800;
        margin-bottom: 12px;
        white-space: normal;
        word-break: break-word;
      }}
      .grid {{
        display: grid;
        grid-template-columns: 30px repeat(10, 42px);
        gap: 4px;
        align-items: center;
        width: fit-content;
      }}
      .coord {{
        text-align: center;
        font-weight: bold;
        color: #1f2937;
      }}
      .cell {{
        width: 42px;
        height: 42px;
        border-radius: 8px;
        border: 1px solid #cbd5e1;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        box-sizing: border-box;
      }}
      .water {{ background: #dbeafe; }}
      .ship {{ background: #93c5fd; }}
      .hit {{ background: #f59e0b; color: white; }}
      .sunk {{ background: #ef4444; color: white; }}
      .preview-ok {{ background: #86efac !important; border: 2px solid #22c55e !important; }}
      .preview-bad {{ background: #fecaca !important; border: 2px solid #ef4444 !important; }}
      .legend {{
        margin-top: 10px;
        color: #6b7280;
        font-size: 13px;
      }}
    </style>
    </head>
    <body>
      <div class="title">{title}</div>
      <div class="grid">
    """

    html += '<div class="coord"></div>'
    for col in COLS:
        html += f'<div class="coord">{col}</div>'

    for r in range(BOARD_SIZE):
        html += f'<div class="coord">{r+1}</div>'
        for c in range(BOARD_SIZE):
            val = board_data[r][c]

            if val == 0:
                cls = "water"
                text = ""
            elif val == 1:
                cls = "ship"
                text = "B"
            elif val == 2:
                cls = "hit"
                text = "X"
            else:
                cls = "sunk"
                text = "H"

            if f"{r},{c}" in preview_set:
                cls = "preview-ok" if preview_valid else "preview-bad"
                text = ""

            html += f'<div class="cell {cls}">{text}</div>'

    html += f"""
      </div>
      <div class="legend">
        Verde = colocación válida · Rojo = colocación inválida
      </div>
    </body>
    </html>
    """
    return html

st.markdown("""
<style>
.block-container {{
    max-width: 1500px;
    padding-top: 1rem;
}}
.app-title {{
    font-size: 2.5rem;
    font-weight: 800;
    line-height: 1.2;
    white-space: normal !important;
    overflow-wrap: anywhere;
    margin-bottom: 0.25rem;
}}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="app-title">🚢 Deep Naval Search</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("Controles")
    st.session_state.selected_ship = st.selectbox("Barco", list(SHIPS.keys()))
    st.session_state.orientation = st.radio("Orientación", ["Horizontal", "Vertical"])

    fila = st.number_input("Fila ancla", min_value=1, max_value=10, value=1)
    columna = st.selectbox("Columna ancla", COLS, index=0)

    if st.button("Previsualizar"):
        st.session_state.preview_anchor = (fila - 1, COLS.index(columna))

    if st.button("Colocar barco"):
        if st.session_state.preview_anchor is not None:
            ok = place_ship(
                st.session_state.board,
                st.session_state.selected_ship,
                st.session_state.preview_anchor[0],
                st.session_state.preview_anchor[1],
                st.session_state.orientation
            )
            if ok:
                st.success("Barco colocado.")
                st.session_state.preview_anchor = None
            else:
                st.error("Colocación inválida.")

components.html(
    render_board_html(
        st.session_state.board,
        st.session_state.preview_anchor,
        SHIPS[st.session_state.selected_ship],
        st.session_state.orientation,
        "Tu tablero"
    ),
    height=560,
    scrolling=False
)

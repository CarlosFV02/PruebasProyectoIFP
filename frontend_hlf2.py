import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import random
from datetime import datetime
from streamlit_plotly_events import plotly_events

# =========================================================
# CONFIG
# =========================================================
st.set_page_config(
    page_title="Deep Naval Search",
    page_icon="🚢",
    layout="wide"
)

BOARD_SIZE = 10
COLS = list("ABCDEFGHIJ")

SHIPS = {
    "Portaaviones": 5,
    "Acorazado": 4,
    "Crucero": 3,
    "Submarino": 3,
    "Destructor": 2
}

# player/enemy board
# 0 = vacío/agua
# 1 = barco
# 2 = tocado
# 3 = hundido
#
# shots/memory board
# 0 = desconocido
# 1 = agua
# 2 = tocado
# 3 = hundido

# =========================================================
# ESTILO
# =========================================================
st.markdown("""
<style>
.block-container {
    padding-top: 0.8rem;
    padding-bottom: 1rem;
    max-width: 1500px;
}
.main-title {
    font-size: 2.3rem;
    font-weight: 800;
    line-height: 1.15;
    margin-bottom: 0.2rem;
    white-space: normal !important;
    word-break: break-word;
}
.subtitle {
    color: #5b6574;
    font-size: 1.02rem;
    margin-bottom: 0.9rem;
}
.panel {
    background: #f8fafc;
    border: 1px solid #e5e7eb;
    border-radius: 14px;
    padding: 0.9rem 1rem;
    margin-bottom: 0.8rem;
}
.small-muted {
    color: #6b7280;
    font-size: 0.9rem;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# HELPERS
# =========================================================
def label_of(row, col):
    return f"{COLS[col]}{row + 1}"

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
        return False, []

    cells = get_cells(row, col, length, orientation)
    for r, c in cells:
        board[r, c] = 1
    return True, cells

def init_enemy():
    board = empty_board()
    positions = {}

    for ship_name, length in SHIPS.items():
        done = False
        while not done:
            orientation = random.choice(["Horizontal", "Vertical"])
            row = random.randint(0, BOARD_SIZE - 1)
            col = random.randint(0, BOARD_SIZE - 1)

            if valid_placement(board, row, col, length, orientation):
                ok, cells = place_ship(board, ship_name, row, col, orientation)
                if ok:
                    positions[ship_name] = cells
                    done = True
    return board, positions

def get_ship_by_cell(ship_positions, row, col):
    for ship_name, cells in ship_positions.items():
        if (row, col) in cells:
            return ship_name
    return None

def ship_is_sunk(board, cells):
    for r, c in cells:
        if board[r, c] not in (2, 3):
            return False
    return True

def mark_sunk(board, cells):
    for r, c in cells:
        board[r, c] = 3

def count_ship_cells_alive(board):
    return int(np.sum(board == 1))

def accuracy(hits, misses, sunk):
    total = hits + misses + sunk
    if total == 0:
        return 0.0
    return ((hits + sunk) / total) * 100

def add_move(actor, target, result, ship_name=None):
    st.session_state.move_log.append({
        "turno_global": len(st.session_state.move_log) + 1,
        "hora": datetime.now().strftime("%H:%M:%S"),
        "actor": actor,
        "casilla": target,
        "resultado": result,
        "barco": ship_name if ship_name else "-"
    })

def all_player_ships_placed():
    return len(st.session_state.player_ship_positions) == len(SHIPS)

def remaining_enemy_ships():
    sunk_names = set(st.session_state.enemy_sunk_ships)
    return {name: size for name, size in SHIPS.items() if name not in sunk_names}

def remaining_player_ships():
    sunk_names = set(st.session_state.player_sunk_ships)
    return {name: size for name, size in SHIPS.items() if name not in sunk_names}

# =========================================================
# HEATMAP REALISTA
# =========================================================
def compute_realistic_heatmap(shots_board, remaining_ships_dict):
    heat = np.zeros((BOARD_SIZE, BOARD_SIZE), dtype=float)

    hit_cells = {(r, c) for r in range(BOARD_SIZE) for c in range(BOARD_SIZE) if shots_board[r, c] == 2}
    blocked = {(r, c) for r in range(BOARD_SIZE) for c in range(BOARD_SIZE) if shots_board[r, c] in (1, 3)}

    if not remaining_ships_dict:
        return heat

    for _, length in remaining_ships_dict.items():
        for orientation in ("Horizontal", "Vertical"):
            max_row = BOARD_SIZE if orientation == "Horizontal" else BOARD_SIZE - length + 1
            max_col = BOARD_SIZE - length + 1 if orientation == "Horizontal" else BOARD_SIZE

            for row in range(max_row):
                for col in range(max_col):
                    cells = get_cells(row, col, length, orientation)

                    if any((r, c) in blocked for r, c in cells):
                        continue

                    cells_set = set(cells)
                    hit_overlap = len(cells_set & hit_cells)

                    if hit_cells and hit_overlap == 0:
                        continue

                    weight = 1.0
                    if hit_overlap > 0:
                        weight = 4 ** hit_overlap

                    for r, c in cells:
                        if shots_board[r, c] == 0:
                            heat[r, c] += weight

    if heat.sum() > 0:
        heat = heat / heat.sum()

    return heat

# =========================================================
# SESSION STATE
# =========================================================
def reset_game():
    st.session_state.phase = "placement"
    st.session_state.turn = "Jugador"
    st.session_state.game_over = False
    st.session_state.winner = None

    st.session_state.player_board = empty_board()
    st.session_state.player_ship_positions = {}
    st.session_state.player_sunk_ships = []

    st.session_state.enemy_board, st.session_state.enemy_ship_positions = init_enemy()
    st.session_state.enemy_sunk_ships = []

    st.session_state.player_shots = empty_board()
    st.session_state.ai_memory = empty_board()

    st.session_state.turn_count = 0
    st.session_state.player_hits = 0
    st.session_state.player_misses = 0
    st.session_state.player_sunk = 0

    st.session_state.ai_hits = 0
    st.session_state.ai_misses = 0
    st.session_state.ai_sunk = 0

    st.session_state.move_log = []
    st.session_state.last_action_text = "Sin movimientos todavía."
    st.session_state.selected_ship = list(SHIPS.keys())[0]
    st.session_state.orientation = "Horizontal"

    # preview colocación
    st.session_state.preview_anchor = None

def ensure_state():
    if "phase" not in st.session_state:
        reset_game()

ensure_state()

# =========================================================
# GAME LOGIC
# =========================================================
def set_preview(row, col):
    st.session_state.preview_anchor = (row, col)

def confirm_place_from_preview():
    if st.session_state.preview_anchor is None:
        st.warning("Primero selecciona una casilla.")
        return

    row, col = st.session_state.preview_anchor
    ship_name = st.session_state.selected_ship
    orientation = st.session_state.orientation

    if ship_name in st.session_state.player_ship_positions:
        st.warning(f"{ship_name} ya está colocado.")
        return

    ok, cells = place_ship(st.session_state.player_board, ship_name, row, col, orientation)
    if not ok:
        st.error("Colocación inválida.")
        return

    st.session_state.player_ship_positions[ship_name] = cells
    st.session_state.last_action_text = f"Colocado {ship_name} en {label_of(row, col)} ({orientation})"
    st.session_state.preview_anchor = None

def confirm_fleet():
    if not all_player_ships_placed():
        st.error("Debes colocar todos los barcos antes de empezar.")
        return
    st.session_state.phase = "battle"
    st.session_state.turn = "Jugador"
    st.session_state.last_action_text = "Flota confirmada. Empieza la partida."

def player_attack(row, col):
    if st.session_state.phase != "battle":
        return
    if st.session_state.turn != "Jugador":
        return
    if st.session_state.game_over:
        return
    if st.session_state.player_shots[row, col] != 0:
        st.warning("Esa casilla ya fue atacada.")
        return

    enemy_val = st.session_state.enemy_board[row, col]
    target_label = label_of(row, col)

    if enemy_val == 0:
        st.session_state.player_shots[row, col] = 1
        st.session_state.player_misses += 1
        st.session_state.last_action_text = f"Jugador dispara en {target_label}: Agua"
        add_move("Jugador", target_label, "Agua")
    else:
        st.session_state.enemy_board[row, col] = 2
        st.session_state.player_shots[row, col] = 2
        st.session_state.player_hits += 1

        ship_name = get_ship_by_cell(st.session_state.enemy_ship_positions, row, col)
        ship_cells = st.session_state.enemy_ship_positions[ship_name]

        if ship_is_sunk(st.session_state.enemy_board, ship_cells):
            mark_sunk(st.session_state.enemy_board, ship_cells)
            for r, c in ship_cells:
                st.session_state.player_shots[r, c] = 3
            if ship_name not in st.session_state.enemy_sunk_ships:
                st.session_state.enemy_sunk_ships.append(ship_name)
            st.session_state.player_sunk += 1
            st.session_state.last_action_text = f"Jugador dispara en {target_label}: Hundido ({ship_name})"
            add_move("Jugador", target_label, "Hundido", ship_name)
        else:
            st.session_state.last_action_text = f"Jugador dispara en {target_label}: Tocado"
            add_move("Jugador", target_label, "Tocado", ship_name)

    st.session_state.turn_count += 1

    if count_ship_cells_alive(st.session_state.enemy_board) == 0:
        st.session_state.game_over = True
        st.session_state.winner = "Jugador"
        return

    st.session_state.turn = "IA"
    ai_turn()

def ai_turn():
    if st.session_state.game_over:
        return

    remaining_for_ai = remaining_player_ships()
    heat = compute_realistic_heatmap(st.session_state.ai_memory, remaining_for_ai)

    if heat.sum() == 0:
        candidates = [(r, c) for r in range(BOARD_SIZE) for c in range(BOARD_SIZE) if st.session_state.ai_memory[r, c] == 0]
        row, col = random.choice(candidates)
    else:
        row, col = np.unravel_index(np.argmax(heat), heat.shape)

    target_label = label_of(row, col)
    player_val = st.session_state.player_board[row, col]

    if player_val == 0:
        st.session_state.ai_memory[row, col] = 1
        st.session_state.ai_misses += 1
        st.session_state.last_action_text = f"IA dispara en {target_label}: Agua"
        add_move("IA", target_label, "Agua")
    else:
        st.session_state.player_board[row, col] = 2
        st.session_state.ai_memory[row, col] = 2
        st.session_state.ai_hits += 1

        ship_name = get_ship_by_cell(st.session_state.player_ship_positions, row, col)
        ship_cells = st.session_state.player_ship_positions[ship_name]

        if ship_is_sunk(st.session_state.player_board, ship_cells):
            mark_sunk(st.session_state.player_board, ship_cells)
            for r, c in ship_cells:
                st.session_state.ai_memory[r, c] = 3
            if ship_name not in st.session_state.player_sunk_ships:
                st.session_state.player_sunk_ships.append(ship_name)
            st.session_state.ai_sunk += 1
            st.session_state.last_action_text = f"IA dispara en {target_label}: Hundido ({ship_name})"
            add_move("IA", target_label, "Hundido", ship_name)
        else:
            st.session_state.last_action_text = f"IA dispara en {target_label}: Tocado"
            add_move("IA", target_label, "Tocado", ship_name)

    if count_ship_cells_alive(st.session_state.player_board) == 0:
        st.session_state.game_over = True
        st.session_state.winner = "IA"
        return

    st.session_state.turn = "Jugador"

# =========================================================
# VISUAL BOARD PLOTLY
# =========================================================
def base_layout(title):
    return dict(
        title=title,
        title_x=0.03,
        margin=dict(l=10, r=10, t=50, b=10),
        height=560,
        xaxis=dict(
            tickmode="array",
            tickvals=list(range(BOARD_SIZE)),
            ticktext=COLS,
            side="top",
            showgrid=False,
            zeroline=False,
            fixedrange=True
        ),
        yaxis=dict(
            tickmode="array",
            tickvals=list(range(BOARD_SIZE)),
            ticktext=[str(i) for i in range(1, BOARD_SIZE + 1)],
            autorange="reversed",
            showgrid=False,
            zeroline=False,
            fixedrange=True
        ),
        plot_bgcolor="white",
        paper_bgcolor="white",
        dragmode=False
    )

def board_to_visual_player(board, preview_cells=None):
    z = np.zeros((BOARD_SIZE, BOARD_SIZE))
    text = np.full((BOARD_SIZE, BOARD_SIZE), "", dtype=object)

    color_map = {
        0: 0,  # agua/vacío
        1: 1,  # barco
        2: 2,  # tocado
        3: 3   # hundido
    }

    symbol_map = {
        0: "",
        1: "B",
        2: "X",
        3: "H"
    }

    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            z[r, c] = color_map[board[r, c]]
            text[r, c] = symbol_map[board[r, c]]

    if preview_cells:
        for r, c in preview_cells:
            if 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE:
                z[r, c] = 4
                text[r, c] = "P"

    fig = go.Figure()

    fig.add_trace(go.Heatmap(
        z=z,
        x=list(range(BOARD_SIZE)),
        y=list(range(BOARD_SIZE)),
        colorscale=[
            [0.00, "#dbeafe"], [0.19, "#dbeafe"],   # agua/vacío
            [0.20, "#93c5fd"], [0.39, "#93c5fd"],   # barco
            [0.40, "#f59e0b"], [0.59, "#f59e0b"],   # tocado
            [0.60, "#ef4444"], [0.79, "#ef4444"],   # hundido
            [0.80, "#34d399"], [1.00, "#34d399"],   # preview
        ],
        showscale=False,
        hoverinfo="skip"
    ))

    xs, ys, labels = [], [], []
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            xs.append(c)
            ys.append(r)
            labels.append(text[r, c])

    fig.add_trace(go.Scatter(
        x=xs,
        y=ys,
        mode="text",
        text=labels,
        textfont=dict(size=18, color="#111827"),
        hoverinfo="skip"
    ))

    fig.update_layout(**base_layout("🛡️ Tu tablero"))
    return fig

def board_to_visual_enemy(shots):
    z = np.zeros((BOARD_SIZE, BOARD_SIZE))
    text = np.full((BOARD_SIZE, BOARD_SIZE), "", dtype=object)

    color_map = {
        0: 0,  # desconocido
        1: 1,  # agua
        2: 2,  # tocado
        3: 3   # hundido
    }

    symbol_map = {
        0: "",
        1: "A",
        2: "X",
        3: "H"
    }

    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            z[r, c] = color_map[shots[r, c]]
            text[r, c] = symbol_map[shots[r, c]]

    fig = go.Figure()

    fig.add_trace(go.Heatmap(
        z=z,
        x=list(range(BOARD_SIZE)),
        y=list(range(BOARD_SIZE)),
        colorscale=[
            [0.00, "#f3f4f6"], [0.24, "#f3f4f6"],   # desconocido
            [0.25, "#bfdbfe"], [0.49, "#bfdbfe"],   # agua
            [0.50, "#f59e0b"], [0.74, "#f59e0b"],   # tocado
            [0.75, "#ef4444"], [1.00, "#ef4444"],   # hundido
        ],
        showscale=False,
        hoverinfo="skip"
    ))

    xs, ys, labels = [], [], []
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            xs.append(c)
            ys.append(r)
            labels.append(text[r, c])

    fig.add_trace(go.Scatter(
        x=xs,
        y=ys,
        mode="text",
        text=labels,
        textfont=dict(size=18, color="#111827"),
        hoverinfo="skip"
    ))

    fig.update_layout(**base_layout("🎯 Tablero enemigo"))
    return fig

def heatmap_figure(heat):
    fig = go.Figure(data=go.Heatmap(
        z=heat,
        x=COLS,
        y=[str(i) for i in range(1, BOARD_SIZE + 1)],
        colorscale="Viridis",
        text=np.round(heat, 2),
        texttemplate="%{text}",
        hovertemplate="Fila %{y}, Columna %{x}<br>Probabilidad=%{z:.3f}<extra></extra>"
    ))

    fig.update_layout(
        title="🧠 Heatmap del jugador",
        title_x=0.03,
        height=700,
        margin=dict(l=10, r=10, t=50, b=10),
        yaxis=dict(autorange="reversed")
    )
    return fig

# =========================================================
# RENDER
# =========================================================
st.markdown('<div class="main-title">🚢 Deep Naval Search</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Versión con tablero visual estable, colores reales y previsualización de colocación</div>',
    unsafe_allow_html=True
)

with st.sidebar:
    st.header("⚙️ Controles")

    if st.button("Reiniciar partida", use_container_width=True):
        reset_game()

    st.divider()
    st.subheader("🚢 Colocación de flota")

    st.session_state.selected_ship = st.selectbox(
        "Barco",
        list(SHIPS.keys()),
        index=list(SHIPS.keys()).index(st.session_state.selected_ship)
    )

    st.session_state.orientation = st.radio(
        "Orientación",
        ["Horizontal", "Vertical"],
        horizontal=True,
        index=0 if st.session_state.orientation == "Horizontal" else 1
    )

    if st.session_state.phase == "placement":
        if st.button("Confirmar colocación seleccionada", use_container_width=True):
            confirm_place_from_preview()

        if st.button("Confirmar flota", use_container_width=True):
            confirm_fleet()

    st.divider()
    st.markdown("**Estado de barcos**")
    for ship_name, size in SHIPS.items():
        estado = "colocado" if ship_name in st.session_state.player_ship_positions else "pendiente"
        st.write(f"{ship_name} ({size}) → {estado}")

    st.divider()
    st.markdown("**Estado actual**")
    st.write(f"Fase: {'Colocación' if st.session_state.phase == 'placement' else 'Batalla'}")
    st.write(f"Turno: {st.session_state.turn}")
    st.caption(st.session_state.last_action_text)

    if st.session_state.game_over:
        if st.session_state.winner == "Jugador":
            st.success("Has ganado.")
        else:
            st.error("Ha ganado la IA.")

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Turnos", st.session_state.turn_count)
m2.metric("Aciertos jugador", st.session_state.player_hits)
m3.metric("Fallos jugador", st.session_state.player_misses)
m4.metric("Hundidos jugador", st.session_state.player_sunk)
m5.metric("Precisión", f"{accuracy(st.session_state.player_hits, st.session_state.player_misses, st.session_state.player_sunk):.1f}%")

st.divider()

tab_juego, tab_heatmap, tab_registro = st.tabs(["Juego", "Heatmap", "Registro"])

with tab_juego:
    c1, c2 = st.columns(2, gap="large")

    preview_cells = None
    if st.session_state.phase == "placement" and st.session_state.preview_anchor is not None:
        pr, pc = st.session_state.preview_anchor
        length = SHIPS[st.session_state.selected_ship]
        preview_cells = get_cells(pr, pc, length, st.session_state.orientation)

    with c1:
        st.markdown("<div class='panel'><b>Tu tablero</b><br><span class='small-muted'>Haz clic para elegir la casilla inicial del barco. Después pulsa “Confirmar colocación seleccionada”.</span></div>", unsafe_allow_html=True)

        player_fig = board_to_visual_player(st.session_state.player_board, preview_cells)
        clicked_player = plotly_events(
            player_fig,
            click_event=True,
            hover_event=False,
            select_event=False,
            override_height=560,
            key="player_plot"
        )

        if clicked_player and st.session_state.phase == "placement":
            point = clicked_player[0]
            row = int(point["y"])
            col = int(point["x"])
            set_preview(row, col)

    with c2:
        st.markdown("<div class='panel'><b>Tablero enemigo</b><br><span class='small-muted'>Haz clic sobre una casilla para disparar.</span></div>", unsafe_allow_html=True)

        enemy_fig = board_to_visual_enemy(st.session_state.player_shots)
        clicked_enemy = plotly_events(
            enemy_fig,
            click_event=True,
            hover_event=False,
            select_event=False,
            override_height=560,
            key="enemy_plot"
        )

        if clicked_enemy and st.session_state.phase == "battle" and st.session_state.turn == "Jugador" and not st.session_state.game_over:
            point = clicked_enemy[0]
            row = int(point["y"])
            col = int(point["x"])
            player_attack(row, col)

with tab_heatmap:
    st.subheader("🧠 Heatmap del jugador sobre el tablero enemigo")
    remaining = remaining_enemy_ships()
    heat = compute_realistic_heatmap(st.session_state.player_shots, remaining)

    if heat.sum() == 0:
        st.info("Todavía no hay suficiente información para un heatmap útil.")
    else:
        best_r, best_c = np.unravel_index(np.argmax(heat), heat.shape)
        st.markdown(
            f"""
            <div class="panel">
                <b>Casilla recomendada:</b> {label_of(best_r, best_c)}<br>
                <b>Probabilidad estimada:</b> {heat[best_r, best_c]:.3f}
            </div>
            """,
            unsafe_allow_html=True
        )
        st.plotly_chart(heatmap_figure(heat), use_container_width=True)

with tab_registro:
    st.subheader("📜 Registro completo de movimientos")

    if not st.session_state.move_log:
        st.info("Todavía no hay movimientos.")
    else:
        df = pd.DataFrame(st.session_state.move_log)
        st.dataframe(df, use_container_width=True, hide_index=True)
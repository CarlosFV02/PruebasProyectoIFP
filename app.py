import streamlit as st
import numpy as np
import pandas as pd
import random
from datetime import datetime
import plotly.express as px

from battleship_component import battleship_board

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

st.markdown("""
<style>
.block-container {
    padding-top: 1rem !important;
    max-width: 1600px !important;
}
h1, h2, h3 {
    line-height: 1.2 !important;
}
.app-title {
    font-size: 2.5rem;
    font-weight: 800;
    line-height: 1.2;
    white-space: normal !important;
    overflow-wrap: anywhere;
    margin-bottom: 0.25rem;
}
.app-subtitle {
    color: #5b6574;
    margin-bottom: 0.9rem;
    font-size: 1.05rem;
}
.panel {
    background: #f8fafc;
    border: 1px solid #dbe3ea;
    border-radius: 14px;
    padding: 0.9rem 1rem;
    margin-bottom: 0.8rem;
}
</style>
""", unsafe_allow_html=True)


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
        placed = False
        while not placed:
            orientation = random.choice(["Horizontal", "Vertical"])
            row = random.randint(0, BOARD_SIZE - 1)
            col = random.randint(0, BOARD_SIZE - 1)

            if valid_placement(board, row, col, length, orientation):
                ok, cells = place_ship(board, ship_name, row, col, orientation)
                if ok:
                    positions[ship_name] = cells
                    placed = True

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

                    overlap = len(set(cells) & hit_cells)

                    if hit_cells and overlap == 0:
                        continue

                    weight = 1.0 if overlap == 0 else 4 ** overlap

                    for r, c in cells:
                        if shots_board[r, c] == 0:
                            heat[r, c] += weight

    if heat.sum() > 0:
        heat = heat / heat.sum()

    return heat


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
    st.session_state.preview_anchor = None


def ensure_state():
    if "phase" not in st.session_state:
        reset_game()


def handle_player_board_event(event):
    if not event or st.session_state.phase != "placement":
        return

    row, col = event["row"], event["col"]

    if event["type"] == "hover":
        st.session_state.preview_anchor = (row, col)

    elif event["type"] == "click":
        st.session_state.preview_anchor = (row, col)
        st.session_state.last_action_text = f"Previsualización en {label_of(row, col)}"


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
    st.session_state.preview_anchor = None
    st.session_state.last_action_text = f"Colocado {ship_name} en {label_of(row, col)} ({orientation})"


def confirm_fleet():
    if not all_player_ships_placed():
        st.error("Debes colocar todos los barcos antes de empezar.")
        return
    st.session_state.phase = "battle"
    st.session_state.turn = "Jugador"
    st.session_state.preview_anchor = None
    st.session_state.last_action_text = "Flota confirmada. Comienza la partida."


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
    target = label_of(row, col)

    if enemy_val == 0:
        st.session_state.player_shots[row, col] = 1
        st.session_state.player_misses += 1
        st.session_state.last_action_text = f"Jugador dispara en {target}: Agua"
        add_move("Jugador", target, "Agua")
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
            st.session_state.last_action_text = f"Jugador dispara en {target}: Hundido ({ship_name})"
            add_move("Jugador", target, "Hundido", ship_name)
        else:
            st.session_state.last_action_text = f"Jugador dispara en {target}: Tocado"
            add_move("Jugador", target, "Tocado", ship_name)

    st.session_state.turn_count += 1

    if count_ship_cells_alive(st.session_state.enemy_board) == 0:
        st.session_state.game_over = True
        st.session_state.winner = "Jugador"
        return

    st.session_state.turn = "IA"
    ai_turn()


def handle_enemy_board_event(event):
    if not event or st.session_state.phase != "battle":
        return
    if event["type"] != "click":
        return
    player_attack(event["row"], event["col"])


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

    target = label_of(row, col)
    player_val = st.session_state.player_board[row, col]

    if player_val == 0:
        st.session_state.ai_memory[row, col] = 1
        st.session_state.ai_misses += 1
        st.session_state.last_action_text = f"IA dispara en {target}: Agua"
        add_move("IA", target, "Agua")
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
            st.session_state.last_action_text = f"IA dispara en {target}: Hundido ({ship_name})"
            add_move("IA", target, "Hundido", ship_name)
        else:
            st.session_state.last_action_text = f"IA dispara en {target}: Tocado"
            add_move("IA", target, "Tocado", ship_name)

    if count_ship_cells_alive(st.session_state.player_board) == 0:
        st.session_state.game_over = True
        st.session_state.winner = "IA"
        return

    st.session_state.turn = "Jugador"


ensure_state()

st.markdown('<div class="app-title">🚢 Deep Naval Search</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="app-subtitle">Versión con componente custom: cuadrícula estable, hover preview y base real para mejorar la colocación</div>',
    unsafe_allow_html=True
)

with st.sidebar:
    st.header("Controles")

    if st.button("Reiniciar partida", use_container_width=True):
        reset_game()

    st.divider()
    st.subheader("Colocación de flota")

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
        if st.button("Confirmar colocación", use_container_width=True):
            confirm_place_from_preview()

        if st.button("Confirmar flota", use_container_width=True):
            confirm_fleet()

    st.divider()
    st.write(f"**Fase:** {'Colocación' if st.session_state.phase == 'placement' else 'Batalla'}")
    st.write(f"**Turno:** {st.session_state.turn}")
    st.caption(st.session_state.last_action_text)

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Turnos", st.session_state.turn_count)
m2.metric("Aciertos jugador", st.session_state.player_hits)
m3.metric("Fallos jugador", st.session_state.player_misses)
m4.metric("Hundidos jugador", st.session_state.player_sunk)
m5.metric("Precisión", f"{accuracy(st.session_state.player_hits, st.session_state.player_misses, st.session_state.player_sunk):.1f}%")

tab_juego, tab_heatmap, tab_registro = st.tabs(["Juego", "Heatmap", "Registro"])

with tab_juego:
    c1, c2 = st.columns(2, gap="large")

    with c1:
        st.markdown("<div class='panel'><b>Tu tablero</b><br>Hover para previsualizar, clic para fijar ancla y luego confirma.</div>", unsafe_allow_html=True)
        player_event = battleship_board(
            board=st.session_state.player_board.tolist(),
            mode="placement" if st.session_state.phase == "placement" else "view",
            selected_ship_length=SHIPS[st.session_state.selected_ship],
            orientation=st.session_state.orientation,
            preview_anchor=st.session_state.preview_anchor,
            key="player_component",
            height=520,
        )
        handle_player_board_event(player_event)

    with c2:
        st.markdown("<div class='panel'><b>Tablero enemigo</b><br>Clic para disparar.</div>", unsafe_allow_html=True)
        enemy_event = battleship_board(
            board=st.session_state.player_shots.tolist(),
            mode="shots" if st.session_state.phase == "battle" else "view",
            selected_ship_length=1,
            orientation="Horizontal",
            preview_anchor=None,
            key="enemy_component",
            height=520,
        )
        handle_enemy_board_event(enemy_event)

with tab_heatmap:
    remaining = remaining_enemy_ships()
    heat = compute_realistic_heatmap(st.session_state.player_shots, remaining)

    if heat.sum() == 0:
        st.info("Todavía no hay suficiente información para un heatmap útil.")
    else:
        best_r, best_c = np.unravel_index(np.argmax(heat), heat.shape)
        st.markdown(
            f"<div class='panel'><b>Casilla recomendada:</b> {label_of(best_r, best_c)}<br><b>Probabilidad:</b> {heat[best_r, best_c]:.3f}</div>",
            unsafe_allow_html=True
        )

        fig = px.imshow(
            heat,
            text_auto=".2f",
            aspect="equal",
            color_continuous_scale="Viridis",
            x=COLS,
            y=[str(i) for i in range(1, BOARD_SIZE + 1)],
            labels={"x": "Columna", "y": "Fila", "color": "Probabilidad"}
        )
        fig.update_layout(height=650, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

with tab_registro:
    st.subheader("Registro completo")
    if not st.session_state.move_log:
        st.info("Todavía no hay movimientos.")
    else:
        df = pd.DataFrame(st.session_state.move_log)
        st.dataframe(df, use_container_width=True, hide_index=True)
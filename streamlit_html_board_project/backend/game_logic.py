"""Utilidades Python para futuras ampliaciones.

Este módulo no es obligatorio para la versión actual, porque la lógica del juego
vive en el componente HTML/JS incrustado. Se deja preparado por si más adelante
quieres mover parte de las reglas a FastAPI o reutilizarlas desde Python.
"""

BOARD_SIZE = 10
SHIPS = {
    "Portaaviones": 5,
    "Acorazado": 4,
    "Crucero": 3,
    "Submarino": 3,
    "Destructor": 2,
}


def get_cells(row: int, col: int, length: int, orientation: str):
    cells = []
    if orientation == "Horizontal":
        for j in range(length):
            cells.append((row, col + j))
    else:
        for i in range(length):
            cells.append((row + i, col))
    return cells


def valid_placement(board, row: int, col: int, length: int, orientation: str) -> bool:
    for r, c in get_cells(row, col, length, orientation):
        if r < 0 or r >= BOARD_SIZE or c < 0 or c >= BOARD_SIZE:
            return False
        if board[r][c] != 0:
            return False
    return True

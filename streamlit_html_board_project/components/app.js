const BOARD_SIZE = 10;
const COLS = "ABCDEFGHIJ".split("");

const SHIPS = [
  { name: "Portaaviones", shortName: "P. avión", size: 5, image: "/static/ships/portaaviones.png" },
  { name: "Acorazado", shortName: "Acoraz.", size: 4, image: "/static/ships/acorazado.png" },
  { name: "Crucero", shortName: "Crucero", size: 3, image: "/static/ships/crucero.png" },
  { name: "Submarino", shortName: "Submar.", size: 3, image: "/static/ships/submarino.png" },
  { name: "Destructor", shortName: "Destr.", size: 2, image: "/static/ships/destructor.png" }
];

const state = {
  phase: "placement",
  turn: "Jugador",
  orientation: "Horizontal",

  playerBoard: createMatrix(0),
  enemyBoard: createMatrix(0),
  playerShots: createMatrix(0),
  aiMemory: createMatrix(0),

  playerShipPositions: {},
  enemyShipPositions: {},
  enemySunkShips: [],
  playerSunkShips: [],

  moveLog: [],

  turns: 0,
  playerHits: 0,
  playerMisses: 0,
  playerSunk: 0,
  aiHits: 0,
  aiMisses: 0,
  aiSunk: 0,

  selectedShip: null,
  dragShip: null,
  previewAnchor: null,
  previewCells: [],
  previewValid: false,
};

function createMatrix(value) {
  return Array.from({ length: BOARD_SIZE }, () => Array(BOARD_SIZE).fill(value));
}

function labelOf(row, col) {
  return `${COLS[col]}${row + 1}`;
}

function getShipDefinition(shipName) {
  return SHIPS.find((s) => s.name === shipName) || null;
}

function getCells(row, col, length, orientation) {
  const cells = [];
  if (orientation === "Horizontal") {
    for (let j = 0; j < length; j++) cells.push([row, col + j]);
  } else {
    for (let i = 0; i < length; i++) cells.push([row + i, col]);
  }
  return cells;
}

function validPlacement(board, row, col, length, orientation) {
  const cells = getCells(row, col, length, orientation);
  for (const [r, c] of cells) {
    if (r < 0 || r >= BOARD_SIZE || c < 0 || c >= BOARD_SIZE) return false;
    if (board[r][c] !== 0) return false;
  }
  return true;
}

function placeShip(board, shipName, row, col, orientation) {
  const ship = getShipDefinition(shipName);
  if (!ship) return false;
  if (!validPlacement(board, row, col, ship.size, orientation)) return false;

  const cells = getCells(row, col, ship.size, orientation);
  for (const [r, c] of cells) {
    board[r][c] = 1;
  }
  return cells;
}

function clearShipFromBoard(board, cells) {
  for (const [r, c] of cells) {
    if (board[r][c] === 1) board[r][c] = 0;
  }
}

function addMove(actor, target, result, ship = "-") {
  state.moveLog.unshift({
    turn: state.moveLog.length + 1,
    time: new Date().toLocaleTimeString(),
    actor,
    target,
    result,
    ship,
  });
}

function allPlayerShipsPlaced() {
  return Object.keys(state.playerShipPositions).length === SHIPS.length;
}

function remainingEnemyShips() {
  return SHIPS.filter((s) => !state.enemySunkShips.includes(s.name));
}

function remainingPlayerShips() {
  return SHIPS.filter((s) => !state.playerSunkShips.includes(s.name));
}

function getShipByCell(shipPositions, row, col) {
  for (const [shipName, cells] of Object.entries(shipPositions)) {
    if (cells.some(([r, c]) => r === row && c === col)) return shipName;
  }
  return null;
}

function shipIsSunk(board, cells) {
  return cells.every(([r, c]) => board[r][c] === 2 || board[r][c] === 3);
}

function markSunk(board, cells) {
  for (const [r, c] of cells) {
    board[r][c] = 3;
  }
}

function countAliveShipCells(board) {
  let count = 0;
  for (const row of board) {
    for (const cell of row) {
      if (cell === 1) count++;
    }
  }
  return count;
}

function accuracy() {
  const total = state.playerHits + state.playerMisses + state.playerSunk;
  if (total === 0) return "0.0%";
  return `${(((state.playerHits + state.playerSunk) / total) * 100).toFixed(1)}%`;
}

function setStatus(text) {
  document.getElementById("status-text").textContent = text;
}

function clearPreview() {
  state.previewAnchor = null;
  state.previewCells = [];
  state.previewValid = false;
}

function activeShipForPlacement() {
  return state.dragShip || state.selectedShip;
}

function resetGame() {
  hideEndgameOverlay();
  state.phase = "placement";
  state.turn = "Jugador";
  state.orientation = "Horizontal";

  state.playerBoard = createMatrix(0);
  state.enemyBoard = createMatrix(0);
  state.playerShots = createMatrix(0);
  state.aiMemory = createMatrix(0);

  state.playerShipPositions = {};
  state.enemyShipPositions = {};
  state.enemySunkShips = [];
  state.playerSunkShips = [];

  state.moveLog = [];

  state.turns = 0;
  state.playerHits = 0;
  state.playerMisses = 0;
  state.playerSunk = 0;
  state.aiHits = 0;
  state.aiMisses = 0;
  state.aiSunk = 0;

  state.selectedShip = null;
  state.dragShip = null;
  clearPreview();

  state.enemyShipPositions = randomEnemyFleet();
  setStatus("Selecciona o arrastra un barco y colócalo en tu tablero.");
  renderAll();
}

function randomEnemyFleet() {
  const positions = {};
  for (const ship of SHIPS) {
    let placed = false;
    while (!placed) {
      const orientation = Math.random() < 0.5 ? "Horizontal" : "Vertical";
      const row = Math.floor(Math.random() * BOARD_SIZE);
      const col = Math.floor(Math.random() * BOARD_SIZE);
      const cells = placeShip(state.enemyBoard, ship.name, row, col, orientation);
      if (cells) {
        positions[ship.name] = cells;
        placed = true;
      }
    }
  }
  return positions;
}

function updatePreviewForShip(shipName, row, col) {
  const ship = getShipDefinition(shipName);
  if (!ship) {
    clearPreview();
    return;
  }
  state.previewAnchor = [row, col];
  state.previewCells = getCells(row, col, ship.size, state.orientation);
  state.previewValid = validPlacement(state.playerBoard, row, col, ship.size, state.orientation);
}

function selectShip(shipName) {
  if (state.phase !== "placement") return;
  state.selectedShip = shipName;
  state.dragShip = null;
  clearPreview();
  setStatus(`${shipName} seleccionado. Haz clic en una casilla o arrástralo al tablero.`);
  renderAll();
}

function placeSelectedShip(shipName, row, col) {
  if (state.phase !== "placement") {
    setStatus("Ya no estás en fase de colocación.");
    return false;
  }
  if (!shipName) {
    setStatus("Selecciona primero un barco.");
    return false;
  }
  if (state.playerShipPositions[shipName]) {
    setStatus(`El ${shipName} ya está colocado.`);
    return false;
  }

  const cells = placeShip(state.playerBoard, shipName, row, col, state.orientation);
  if (!cells) {
    updatePreviewForShip(shipName, row, col);
    setStatus(`No se puede colocar ${shipName} en ${labelOf(row, col)} con orientación ${state.orientation}.`);
    renderAll();
    return false;
  }

  state.playerShipPositions[shipName] = cells;
  state.selectedShip = null;
  state.dragShip = null;
  clearPreview();
  setStatus(`${shipName} colocado correctamente en ${labelOf(row, col)}.`);
  renderAll();
  return true;
}

function removePlacedShip(shipName) {
  const cells = state.playerShipPositions[shipName];
  if (!cells) return;
  clearShipFromBoard(state.playerBoard, cells);
  delete state.playerShipPositions[shipName];
  state.selectedShip = shipName;
  state.dragShip = null;
  clearPreview();
  setStatus(`${shipName} retirado. Colócalo de nuevo donde quieras.`);
  renderAll();
}

function renderShipList() {
  const container = document.getElementById("ship-list");
  container.innerHTML = "";

  for (const ship of SHIPS) {
    const placed = !!state.playerShipPositions[ship.name];
    const selected = activeShipForPlacement() === ship.name;

    const card = document.createElement("div");
    card.className = "ship-card";
    if (placed) card.classList.add("placed");
    if (selected) card.classList.add("selected");

    card.innerHTML = `
      <div class="ship-card-top">
        <img class="ship-thumb" src="${ship.image}" alt="${ship.name}" onerror="this.style.display='none'">
        <div>
          <div class="ship-name">${ship.shortName || ship.name}</div>
          <div class="ship-size">${ship.size} casillas · ${placed ? "colocado" : "pendiente"}</div>
        </div>
      </div>
      <div class="ship-mini-preview ${state.orientation === "Horizontal" ? "horizontal" : "vertical"}">
        ${Array.from({ length: ship.size }, (_, idx) => `<span class="mini-segment ${miniSegmentClass(ship.size, idx)}"></span>`).join("")}
      </div>
      ${placed ? `<button class="mini-btn" data-remove="${ship.name}">Quitar / recolocar</button>` : ""}
    `;

    if (!placed && state.phase === "placement") {
      card.draggable = true;
      card.addEventListener("dragstart", (e) => {
        state.dragShip = ship.name;
        state.selectedShip = ship.name;
        e.dataTransfer.setData("text/plain", ship.name);
        e.dataTransfer.effectAllowed = "move";
        setStatus(`Arrastrando ${ship.name}. Suéltalo sobre tu tablero.`);
        renderShipList();
      });

      card.addEventListener("dragend", () => {
        state.dragShip = null;
        clearPreview();
        renderPlayerBoard();
        renderShipList();
      });

      card.addEventListener("click", () => {
        selectShip(ship.name);
      });
    }

    container.appendChild(card);
  }

  container.querySelectorAll("[data-remove]").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      removePlacedShip(btn.dataset.remove);
    });
  });
}

function miniSegmentClass(size, index) {
  if (size === 1) return "single";
  if (index === 0) return "start";
  if (index === size - 1) return "end";
  return "middle";
}

function shipSegmentInfo(cells, row, col) {
  const index = cells.findIndex(([r, c]) => r === row && c === col);
  if (index === -1) return null;
  const horizontal = cells.length < 2 ? true : cells[0][0] === cells[1][0];
  let segment = "middle";
  if (cells.length === 1) segment = "single";
  else if (index === 0) segment = "start";
  else if (index === cells.length - 1) segment = "end";
  return { orientation: horizontal ? "horizontal" : "vertical", segment };
}

function createShipPiece(shipName, segmentInfo) {
  const piece = document.createElement("div");
  piece.className = `ship-piece ${segmentInfo.orientation} ${segmentInfo.segment}`;

  const img = document.createElement("img");
  img.src = getShipDefinition(shipName)?.image || "";
  img.alt = shipName;
  img.className = "ship-piece-image";
  piece.appendChild(img);

  const cap = document.createElement("div");
  cap.className = "ship-piece-cap";
  piece.appendChild(cap);
  return piece;
}

function createBoardGrid(container, boardType) {
  container.innerHTML = "";
  const grid = document.createElement("div");
  grid.className = "board-grid";

  const corner = document.createElement("div");
  corner.className = "coord";
  grid.appendChild(corner);

  for (const letter of COLS) {
    const d = document.createElement("div");
    d.className = "top-coord";
    d.textContent = letter;
    grid.appendChild(d);
  }

  const previewSet = new Set(state.previewCells.map(([r, c]) => `${r},${c}`));

  for (let r = 0; r < BOARD_SIZE; r++) {
    const rowLabel = document.createElement("div");
    rowLabel.className = "coord";
    rowLabel.textContent = r + 1;
    grid.appendChild(rowLabel);

    for (let c = 0; c < BOARD_SIZE; c++) {
      const cell = document.createElement("div");
      cell.className = "cell";
      cell.dataset.row = String(r);
      cell.dataset.col = String(c);

      let value = 0;
      let text = "";

      if (boardType === "player") {
        value = state.playerBoard[r][c];
        if (value === 0) cell.classList.add("water");
        if (value === 1) {
          cell.classList.add("ship");
          const shipName = getShipByCell(state.playerShipPositions, r, c);
          if (shipName) {
            const segmentInfo = shipSegmentInfo(state.playerShipPositions[shipName], r, c);
            if (segmentInfo) cell.appendChild(createShipPiece(shipName, segmentInfo));
          }
        }
        if (value === 2) {
          cell.classList.add("hit");
          text = "✕";
        }
        if (value === 3) {
          cell.classList.add("sunk");
          text = "✕";
        }
      } else {
        value = state.playerShots[r][c];
        if (value === 0) cell.classList.add("unknown");
        if (value === 1) {
          cell.classList.add("water");
          text = "·";
        }
        if (value === 2) {
          cell.classList.add("hit");
          text = "✕";
        }
        if (value === 3) {
          cell.classList.add("sunk");
          text = "✕";
        }
      }

      if (boardType === "player" && state.phase === "placement" && previewSet.has(`${r},${c}`)) {
        cell.className = `cell ${state.previewValid ? "preview" : "preview-bad"}`;
        const shipName = activeShipForPlacement();
        if (shipName) {
          const segmentInfo = shipSegmentInfo(state.previewCells, r, c);
          if (segmentInfo) {
            const ghost = document.createElement("div");
            ghost.className = `ship-piece preview-piece ${segmentInfo.orientation} ${segmentInfo.segment}`;
            cell.appendChild(ghost);
          }
        }
      }

      if (text) {
        const span = document.createElement("span");
        span.textContent = text;
        span.className = "cell-mark";
        cell.appendChild(span);
      }
      grid.appendChild(cell);
    }
  }
  container.appendChild(grid);
}

function updatePreviewAt(row, col) {
  const shipName = activeShipForPlacement();
  if (!shipName || state.phase !== "placement") return;
  const prevAnchor = state.previewAnchor ? `${state.previewAnchor[0]},${state.previewAnchor[1]}` : null;
  updatePreviewForShip(shipName, row, col);
  const newAnchor = state.previewAnchor ? `${state.previewAnchor[0]},${state.previewAnchor[1]}` : null;
  if (prevAnchor !== newAnchor) renderPlayerBoard();
}

function setupBoardInteractions() {
  const playerBoard = document.getElementById("player-board");
  const enemyBoard = document.getElementById("enemy-board");

  playerBoard.addEventListener("click", (e) => {
    const cell = e.target.closest(".cell");
    if (!cell || state.phase !== "placement") return;
    const row = Number(cell.dataset.row);
    const col = Number(cell.dataset.col);
    const value = state.playerBoard[row][col];
    if (value === 1) {
      const shipName = getShipByCell(state.playerShipPositions, row, col);
      if (shipName) {
        setStatus(`${shipName} ya está colocado. Puedes quitarlo desde la lista lateral.`);
        return;
      }
    }
    placeSelectedShip(activeShipForPlacement(), row, col);
  });

  playerBoard.addEventListener("mousemove", (e) => {
    const cell = e.target.closest(".cell");
    if (!cell) return;
    updatePreviewAt(Number(cell.dataset.row), Number(cell.dataset.col));
  });

  playerBoard.addEventListener("mouseleave", () => {
    if (state.previewCells.length) {
      clearPreview();
      renderPlayerBoard();
    }
  });

  playerBoard.addEventListener("dragover", (e) => {
    if (state.phase !== "placement") return;
    e.preventDefault();
    const cell = e.target.closest(".cell");
    if (!cell) return;
    updatePreviewAt(Number(cell.dataset.row), Number(cell.dataset.col));
  });

  playerBoard.addEventListener("drop", (e) => {
    if (state.phase !== "placement") return;
    e.preventDefault();
    const cell = e.target.closest(".cell");
    if (!cell) return;
    const shipName = state.dragShip || e.dataTransfer.getData("text/plain") || state.selectedShip;
    placeSelectedShip(shipName, Number(cell.dataset.row), Number(cell.dataset.col));
  });

  enemyBoard.addEventListener("click", (e) => {
    const cell = e.target.closest(".cell");
    if (!cell || state.phase !== "battle" || state.turn !== "Jugador") return;
    playerAttack(Number(cell.dataset.row), Number(cell.dataset.col));
  });
}

function renderPlayerBoard() {
  createBoardGrid(document.getElementById("player-board"), "player");
}

function renderEnemyBoard() {
  createBoardGrid(document.getElementById("enemy-board"), "enemy");
}

function playerAttack(row, col) {
  if (state.phase !== "battle" || state.turn !== "Jugador") return;
  if (state.playerShots[row][col] !== 0) {
    setStatus("Esa casilla ya fue atacada.");
    return;
  }

  const target = labelOf(row, col);
  const enemyVal = state.enemyBoard[row][col];
  let success = false;

  if (enemyVal === 0) {
    state.playerShots[row][col] = 1;
    state.playerMisses++;
    addMove("Jugador", target, "Agua");
    setStatus(`Jugador dispara en ${target}: Agua`);
  } else {
    success = true;
    state.enemyBoard[row][col] = 2;
    state.playerShots[row][col] = 2;
    state.playerHits++;

    const shipName = getShipByCell(state.enemyShipPositions, row, col);
    const shipCells = state.enemyShipPositions[shipName];

    if (shipIsSunk(state.enemyBoard, shipCells)) {
      markSunk(state.enemyBoard, shipCells);
      for (const [rr, cc] of shipCells) state.playerShots[rr][cc] = 3;
      if (!state.enemySunkShips.includes(shipName)) state.enemySunkShips.push(shipName);
      state.playerSunk++;
      addMove("Jugador", target, "Hundido", shipName);
      setStatus(`Jugador dispara en ${target}: Hundido (${shipName}). Sigues tirando.`);
    } else {
      addMove("Jugador", target, "Tocado", shipName);
      setStatus(`Jugador dispara en ${target}: Tocado. Sigues tirando.`);
    }
  }

  state.turns++;
  renderAll();

  if (countAliveShipCells(state.enemyBoard) === 0) {
    state.phase = "finished";
    state.turn = "-";
    setStatus("Has ganado la partida.");
    renderAll();
    showEndgameOverlay("win");
    return;
  }

  if (!success) {
    state.turn = "IA";
    renderAll();
    setTimeout(() => aiTurn(), 450);
  } else {
    state.turn = "Jugador";
    renderAll();
  }
}

function aiTurn() {
  if (state.phase !== "battle") return;

  const heat = computeRealisticHeatmap(state.aiMemory, remainingPlayerShips());
  let best = null;
  let bestValue = -1;

  for (let r = 0; r < BOARD_SIZE; r++) {
    for (let c = 0; c < BOARD_SIZE; c++) {
      if (state.aiMemory[r][c] === 0 && heat[r][c] > bestValue) {
        bestValue = heat[r][c];
        best = [r, c];
      }
    }
  }

  if (!best) {
    for (let r = 0; r < BOARD_SIZE; r++) {
      for (let c = 0; c < BOARD_SIZE; c++) {
        if (state.aiMemory[r][c] === 0) {
          best = [r, c];
          break;
        }
      }
      if (best) break;
    }
  }

  const [row, col] = best;
  const target = labelOf(row, col);
  const playerVal = state.playerBoard[row][col];
  let success = false;

  if (playerVal === 0) {
    state.aiMemory[row][col] = 1;
    state.aiMisses++;
    addMove("IA", target, "Agua");
    setStatus(`IA dispara en ${target}: Agua`);
  } else {
    success = true;
    state.playerBoard[row][col] = 2;
    state.aiMemory[row][col] = 2;
    state.aiHits++;

    const shipName = getShipByCell(state.playerShipPositions, row, col);
    const shipCells = state.playerShipPositions[shipName];

    if (shipIsSunk(state.playerBoard, shipCells)) {
      markSunk(state.playerBoard, shipCells);
      for (const [rr, cc] of shipCells) state.aiMemory[rr][cc] = 3;
      if (!state.playerSunkShips.includes(shipName)) state.playerSunkShips.push(shipName);
      state.aiSunk++;
      addMove("IA", target, "Hundido", shipName);
      setStatus(`IA dispara en ${target}: Hundido (${shipName}). La IA sigue tirando.`);
    } else {
      addMove("IA", target, "Tocado", shipName);
      setStatus(`IA dispara en ${target}: Tocado. La IA sigue tirando.`);
    }
  }

  renderAll();

  if (countAliveShipCells(state.playerBoard) === 0) {
    state.phase = "finished";
    state.turn = "-";
    setStatus("La IA ha ganado la partida.");
    renderAll();
    showEndgameOverlay("lose");
    return;
  }

  if (success) {
    state.turn = "IA";
    renderAll();
    setTimeout(() => aiTurn(), 450);
  } else {
    state.turn = "Jugador";
    renderAll();
  }
}

function computeRealisticHeatmap(shotsBoard, remainingShips) {
  const heat = createMatrix(0);
  const hitCells = [];
  const blocked = new Set();

  for (let r = 0; r < BOARD_SIZE; r++) {
    for (let c = 0; c < BOARD_SIZE; c++) {
      if (shotsBoard[r][c] === 2) hitCells.push([r, c]);
      if (shotsBoard[r][c] === 1 || shotsBoard[r][c] === 3) blocked.add(`${r},${c}`);
    }
  }

  for (const ship of remainingShips) {
    for (const orientation of ["Horizontal", "Vertical"]) {
      const maxRow = orientation === "Horizontal" ? BOARD_SIZE : BOARD_SIZE - ship.size + 1;
      const maxCol = orientation === "Horizontal" ? BOARD_SIZE - ship.size + 1 : BOARD_SIZE;

      for (let row = 0; row < maxRow; row++) {
        for (let col = 0; col < maxCol; col++) {
          const cells = getCells(row, col, ship.size, orientation);
          let invalid = false;

          for (const [r, c] of cells) {
            if (blocked.has(`${r},${c}`)) {
              invalid = true;
              break;
            }
          }
          if (invalid) continue;

          const overlap = cells.filter(([r, c]) => shotsBoard[r][c] === 2).length;
          if (hitCells.length > 0 && overlap === 0) continue;
          const weight = overlap > 0 ? Math.pow(4, overlap) : 1;

          for (const [r, c] of cells) {
            if (shotsBoard[r][c] === 0) heat[r][c] += weight;
          }
        }
      }
    }
  }

  let sum = 0;
  for (let r = 0; r < BOARD_SIZE; r++) {
    for (let c = 0; c < BOARD_SIZE; c++) sum += heat[r][c];
  }

  if (sum > 0) {
    for (let r = 0; r < BOARD_SIZE; r++) {
      for (let c = 0; c < BOARD_SIZE; c++) heat[r][c] /= sum;
    }
  }
  return heat;
}

function heatColor(value) {
  if (value <= 0) return "#f3f4f6";
  if (value < 0.05) return "#dbeafe";
  if (value < 0.1) return "#93c5fd";
  if (value < 0.15) return "#60a5fa";
  if (value < 0.2) return "#34d399";
  return "#f59e0b";
}

function renderHeatmap() {
  const container = document.getElementById("heatmap-grid");
  container.innerHTML = "";

  const heat = computeRealisticHeatmap(state.playerShots, remainingEnemyShips());
  let best = null;
  let bestValue = -1;

  const corner = document.createElement("div");
  corner.className = "coord";
  container.appendChild(corner);

  for (const letter of COLS) {
    const d = document.createElement("div");
    d.className = "top-coord";
    d.textContent = letter;
    container.appendChild(d);
  }

  for (let r = 0; r < BOARD_SIZE; r++) {
    const rowLabel = document.createElement("div");
    rowLabel.className = "coord";
    rowLabel.textContent = r + 1;
    container.appendChild(rowLabel);

    for (let c = 0; c < BOARD_SIZE; c++) {
      const value = heat[r][c];
      const cell = document.createElement("div");
      cell.className = "heat-cell";
      cell.style.background = heatColor(value);
      cell.textContent = value > 0 ? value.toFixed(2) : "";

      if (value > bestValue) {
        bestValue = value;
        best = [r, c];
      }
      container.appendChild(cell);
    }
  }

  const bestText = document.getElementById("heatmap-best-cell");
  if (best && bestValue > 0) {
    bestText.innerHTML = `<strong>Casilla recomendada:</strong> ${labelOf(best[0], best[1])} · <strong>Probabilidad:</strong> ${bestValue.toFixed(3)}`;
  } else {
    bestText.textContent = "Todavía no hay suficiente información para una recomendación útil.";
  }
}

function renderLog() {
  const container = document.getElementById("log-list");
  container.innerHTML = "";
  if (state.moveLog.length === 0) {
    container.innerHTML = `<div class="log-item">Todavía no hay movimientos.</div>`;
    return;
  }

  for (const item of state.moveLog) {
    const div = document.createElement("div");
    div.className = "log-item";
    div.innerHTML = `
      <strong>#${item.turn}</strong> · ${item.time}<br>
      <strong>${item.actor}</strong> → ${item.target} · ${item.result} · ${item.ship}
    `;
    container.appendChild(div);
  }
}

function renderMetrics() {
  document.getElementById("metric-turns").textContent = state.turns;
  document.getElementById("metric-hits").textContent = state.playerHits;
  document.getElementById("metric-misses").textContent = state.playerMisses;
  document.getElementById("metric-sunk").textContent = state.playerSunk;
  document.getElementById("metric-accuracy").textContent = accuracy();
}

function renderMeta() {
  document.getElementById("phase-label").textContent =
    state.phase === "placement" ? "Colocación" : state.phase === "battle" ? "Batalla" : "Finalizada";
  document.getElementById("turn-label").textContent = state.turn;
  document.getElementById("orientation-label").textContent = state.orientation;
  document.getElementById("start-btn").disabled = !allPlayerShipsPlaced() || state.phase !== "placement";

  const gameLayout = document.querySelector(".triple-layout");
  if (gameLayout) {
    gameLayout.classList.toggle("battle-ready", state.phase !== "placement");
  }
}


function getEndgameStats(result) {
  return [
    { label: 'Turnos jugados', value: state.turns },
    { label: 'Aciertos del jugador', value: state.playerHits + state.playerSunk },
    { label: 'Hundidos del jugador', value: state.playerSunk },
    { label: result === 'win' ? 'Precisión final' : 'Barcos hundidos por la IA', value: result === 'win' ? accuracy() : state.aiSunk },
  ];
}

function renderEndgameStats(result) {
  const stats = document.getElementById('endgame-stats');
  stats.innerHTML = getEndgameStats(result).map((item) => `
    <div class="endgame-stat">
      <span>${item.label}</span>
      <strong>${item.value}</strong>
    </div>
  `).join('');
}

function clearEndgameEffects() {
  const effects = document.getElementById('endgame-effects');
  effects.innerHTML = '';
}

function launchConfetti() {
  const effects = document.getElementById('endgame-effects');
  clearEndgameEffects();
  const shapes = ['rect', 'circle'];
  for (let i = 0; i < 110; i++) {
    const piece = document.createElement('span');
    piece.className = `confetti-piece ${shapes[i % shapes.length] === 'circle' ? 'circle' : ''}`;
    piece.style.left = `${Math.random() * 100}%`;
    piece.style.animationDuration = `${3.8 + Math.random() * 2.2}s`;
    piece.style.animationDelay = `${Math.random() * 0.5}s`;
    piece.style.setProperty('--drift', `${-160 + Math.random() * 320}px`);
    piece.style.setProperty('--spin', `${180 + Math.random() * 1080}deg`);
    piece.style.background = `hsl(${Math.floor(Math.random() * 360)}, 95%, 60%)`;
    effects.appendChild(piece);
  }
}

function launchDefeatEffect() {
  const effects = document.getElementById('endgame-effects');
  clearEndgameEffects();

  const ring = document.createElement('span');
  ring.className = 'explosion-ring';
  effects.appendChild(ring);

  for (let i = 0; i < 18; i++) {
    const spark = document.createElement('span');
    spark.className = 'explosion-spark';
    spark.style.setProperty('--angle', `${i * 20}deg`);
    spark.style.setProperty('--distance', `${90 + Math.random() * 160}px`);
    effects.appendChild(spark);
  }

  const card = document.getElementById('endgame-card');
  card.classList.remove('shake');
  void card.offsetWidth;
  card.classList.add('shake');
}


function showEndgameOverlay(result) {
  const overlay = document.getElementById("endgame-overlay");
  const card = document.getElementById("endgame-card");
  const badge = document.getElementById("endgame-badge");
  const icon = document.getElementById("endgame-icon");
  const title = document.getElementById("endgame-title");
  const message = document.getElementById("endgame-message");

  card.classList.remove("win", "lose", "shake");

  if (result === "win") {
    card.classList.add("win");
    badge.textContent = "Victoria";
    icon.textContent = "🏆";
    title.textContent = "¡Has ganado!";
    message.textContent = `Has hundido toda la flota enemiga en ${state.turns} turnos. Partidaza.`;
    launchConfetti();
  } else {
    card.classList.add("lose");
    badge.textContent = "Derrota";
    icon.textContent = "💥";
    title.textContent = "Has perdido";
    message.textContent = "La IA ha hundido toda tu flota. Revisa las estadísticas finales y vuelve a intentarlo.";
    launchDefeatEffect();
  }

  renderEndgameStats(result);
  overlay.classList.remove("hidden");
  overlay.setAttribute("aria-hidden", "false");
}

function hideEndgameOverlay() {
  const overlay = document.getElementById("endgame-overlay");
  overlay.classList.add("hidden");
  overlay.setAttribute("aria-hidden", "true");
  clearEndgameEffects();
}

function renderAll() {
  renderShipList();
  renderPlayerBoard();
  renderEnemyBoard();
  renderHeatmap();
  renderLog();
  renderMetrics();
  renderMeta();
}

document.getElementById("rotate-btn").addEventListener("click", () => {
  state.orientation = state.orientation === "Horizontal" ? "Vertical" : "Horizontal";
  const shipName = activeShipForPlacement();
  if (shipName && state.previewAnchor) {
    const [row, col] = state.previewAnchor;
    updatePreviewForShip(shipName, row, col);
  }
  setStatus(`Orientación actual: ${state.orientation}`);
  renderAll();
});

document.getElementById("start-btn").addEventListener("click", () => {
  if (!allPlayerShipsPlaced()) {
    setStatus("Debes colocar los 5 barcos antes de empezar.");
    return;
  }
  state.phase = "battle";
  state.turn = "Jugador";
  state.selectedShip = null;
  state.dragShip = null;
  clearPreview();
  setStatus("Partida iniciada. Ya puedes disparar al tablero enemigo.");
  renderAll();
});

document.getElementById("reset-btn").addEventListener("click", resetGame);

document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach((t) => t.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(btn.dataset.tab).classList.add("active");
  });
});

setupBoardInteractions();
resetGame();


document.getElementById("play-again-btn").addEventListener("click", resetGame);
document.getElementById("close-overlay-btn").addEventListener("click", hideEndgameOverlay);
document.getElementById("endgame-overlay").addEventListener("click", (e) => {
  if (e.target.id === "endgame-overlay") hideEndgameOverlay();
});

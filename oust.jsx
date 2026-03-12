import { useState, useMemo } from "react";

// ── Hex grid math (axial coordinates) ──────────────────────────────
function hexNeighbors(q, r) {
  return [
    [q + 1, r], [q - 1, r],
    [q, r + 1], [q, r - 1],
    [q + 1, r - 1], [q - 1, r + 1],
  ];
}

function generateHexGrid(size) {
  const cells = [];
  for (let q = -(size - 1); q <= size - 1; q++) {
    for (let r = -(size - 1); r <= size - 1; r++) {
      if (Math.abs(q + r) <= size - 1) cells.push({ q, r });
    }
  }
  return cells;
}

function key(q, r) { return `${q},${r}`; }

function findGroup(board, startKey) {
  const color = board.get(startKey);
  if (!color) return [];
  const visited = new Set([startKey]);
  const queue = [startKey];
  while (queue.length > 0) {
    const cur = queue.shift();
    const [cq, cr] = cur.split(",").map(Number);
    for (const [nq, nr] of hexNeighbors(cq, cr)) {
      const nk = key(nq, nr);
      if (!visited.has(nk) && board.get(nk) === color) {
        visited.add(nk);
        queue.push(nk);
      }
    }
  }
  return [...visited];
}

// Determine if placing at (q,r) is non-capturing, capturing, or invalid
function classifyPlacement(board, q, r, player) {
  const enemy = player === "red" ? "blue" : "red";
  const k = key(q, r);
  if (board.has(k)) return { type: "invalid" };

  const nbrs = hexNeighbors(q, r);
  const hasFriendly = nbrs.some(([nq, nr]) => board.get(key(nq, nr)) === player);

  if (!hasFriendly) return { type: "non-capturing" };

  // Build the new merged group via BFS from this cell through friendly stones
  const newGroup = new Set([k]);
  const queue = [];
  for (const [nq, nr] of nbrs) {
    const nk = key(nq, nr);
    if (board.get(nk) === player && !newGroup.has(nk)) {
      newGroup.add(nk);
      queue.push(nk);
    }
  }
  while (queue.length > 0) {
    const cur = queue.shift();
    const [cq, cr] = cur.split(",").map(Number);
    for (const [nq, nr] of hexNeighbors(cq, cr)) {
      const nk = key(nq, nr);
      if (board.get(nk) === player && !newGroup.has(nk)) {
        newGroup.add(nk);
        queue.push(nk);
      }
    }
  }

  // Find all enemy groups adjacent to the new group
  const enemyVisited = new Set();
  const enemyGroups = [];
  for (const mk of newGroup) {
    const [mq, mr] = mk.split(",").map(Number);
    for (const [nq, nr] of hexNeighbors(mq, mr)) {
      const nk = key(nq, nr);
      if (board.get(nk) === enemy && !enemyVisited.has(nk)) {
        const grp = findGroup(board, nk);
        for (const gc of grp) enemyVisited.add(gc);
        enemyGroups.push(grp);
      }
    }
  }

  if (enemyGroups.length === 0) return { type: "invalid" };

  const newGroupSize = newGroup.size;
  for (const grp of enemyGroups) {
    if (grp.length >= newGroupSize) return { type: "invalid" };
  }

  return { type: "capturing", capturedCells: enemyGroups.flat() };
}

function getValidPlacements(board, cells, player) {
  const valid = new Set();
  for (const { q, r } of cells) {
    const result = classifyPlacement(board, q, r, player);
    if (result.type !== "invalid") valid.add(key(q, r));
  }
  return valid;
}

function countStones(board) {
  let red = 0, blue = 0;
  for (const color of board.values()) {
    if (color === "red") red++;
    else blue++;
  }
  return { red, blue };
}

// ── Hex rendering helpers ──────────────────────────────────────────
const HEX_SIZE = 28;
const SQRT3 = Math.sqrt(3);

function hexToPixel(q, r) {
  return {
    x: HEX_SIZE * (SQRT3 * q + (SQRT3 / 2) * r),
    y: HEX_SIZE * (1.5 * r),
  };
}

function hexPoints(cx, cy, size) {
  const pts = [];
  for (let i = 0; i < 6; i++) {
    const angle = (Math.PI / 180) * (60 * i - 30);
    pts.push(`${cx + size * Math.cos(angle)},${cy + size * Math.sin(angle)}`);
  }
  return pts.join(" ");
}

// ── Main Component ─────────────────────────────────────────────────
const BOARD_SIZES = [5, 6, 7, 8, 9];

export default function OustGame() {
  const [boardSize, setBoardSize] = useState(7);
  const [board, setBoard] = useState(new Map());
  const [currentPlayer, setCurrentPlayer] = useState("red");
  const [gameOver, setGameOver] = useState(false);
  const [winner, setWinner] = useState(null);
  const [showRules, setShowRules] = useState(false);
  const [showMenu, setShowMenu] = useState(true);
  const [errorMsg, setErrorMsg] = useState("");
  const [mustContinue, setMustContinue] = useState(false);
  const [turnHistory, setTurnHistory] = useState([]);
  const [lastPlacedKeys, setLastPlacedKeys] = useState(new Set());
  const [passMessage, setPassMessage] = useState("");

  const cells = useMemo(() => generateHexGrid(boardSize), [boardSize]);
  const stones = useMemo(() => countStones(board), [board]);
  const validSet = useMemo(
    () => gameOver ? new Set() : getValidPlacements(board, cells, currentPlayer),
    [board, cells, currentPlayer, gameOver]
  );

  function resetGame(size) {
    setBoardSize(size || boardSize);
    setBoard(new Map());
    setCurrentPlayer("red");
    setGameOver(false);
    setWinner(null);
    setMustContinue(false);
    setTurnHistory([]);
    setLastPlacedKeys(new Set());
    setPassMessage("");
    setErrorMsg("");
    setShowMenu(false);
  }

  function endTurn(newBoard) {
    const next = currentPlayer === "red" ? "blue" : "red";
    const nextValid = getValidPlacements(newBoard, cells, next);

    setBoard(newBoard);
    setMustContinue(false);
    setTurnHistory([]);
    setLastPlacedKeys(new Set());
    setErrorMsg("");

    if (nextValid.size > 0) {
      setCurrentPlayer(next);
      setPassMessage("");
    } else {
      setPassMessage(`${next === "red" ? "Red" : "Blue"} has no valid placements \u2014 passed.`);
    }
  }

  function handleCellClick(q, r) {
    if (gameOver) return;
    const k = key(q, r);
    if (board.has(k) || !validSet.has(k)) return;

    const result = classifyPlacement(board, q, r, currentPlayer);
    if (result.type === "invalid") return;

    const newBoard = new Map(board);
    newBoard.set(k, currentPlayer);

    if (result.type === "non-capturing") {
      endTurn(newBoard);
      return;
    }

    // Capturing placement
    for (const ck of result.capturedCells) newBoard.delete(ck);

    // Check win
    const enemy = currentPlayer === "red" ? "blue" : "red";
    let enemyHas = false;
    for (const c of newBoard.values()) { if (c === enemy) { enemyHas = true; break; } }

    if (!enemyHas && stones[enemy] > 0) {
      setBoard(newBoard);
      setGameOver(true);
      setWinner(currentPlayer);
      setLastPlacedKeys(new Set([...lastPlacedKeys, k]));
      setErrorMsg("");
      return;
    }

    // Check if must continue or end turn
    const moreValid = getValidPlacements(newBoard, cells, currentPlayer);
    if (moreValid.size === 0) {
      endTurn(newBoard);
      return;
    }

    // Must continue placing
    setBoard(newBoard);
    setMustContinue(true);
    setTurnHistory([...turnHistory, new Map(board)]);
    setLastPlacedKeys(new Set([...lastPlacedKeys, k]));
    setPassMessage("");
    setErrorMsg("");
  }

  function undoLastPlacement() {
    if (turnHistory.length === 0) return;
    const prevBoard = turnHistory[turnHistory.length - 1];
    setBoard(prevBoard);
    setTurnHistory(turnHistory.slice(0, -1));
    setMustContinue(turnHistory.length > 1);
    setLastPlacedKeys(new Set());
    setErrorMsg("");
    setPassMessage("");
  }

  // ── SVG board rendering ──────────────────────────────────────────
  const allPixels = cells.map(c => hexToPixel(c.q, c.r));
  const margin = HEX_SIZE * 2;
  const xs = allPixels.map(p => p.x);
  const ys = allPixels.map(p => p.y);
  const minX = Math.min(...xs) - margin;
  const maxX = Math.max(...xs) + margin;
  const minY = Math.min(...ys) - margin;
  const maxY = Math.max(...ys) + margin;
  const viewBox = `${minX} ${minY} ${maxX - minX} ${maxY - minY}`;

  // ── Styles ───────────────────────────────────────────────────────
  const styles = {
    container: {
      minHeight: "100vh",
      background: "#1a1612",
      color: "#e8dcc8",
      fontFamily: "'Courier New', monospace",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      userSelect: "none",
      WebkitUserSelect: "none",
      touchAction: "manipulation",
      overflow: "hidden",
    },
    header: {
      width: "100%",
      textAlign: "center",
      padding: "12px 0 4px",
      borderBottom: "1px solid #3a3228",
    },
    title: {
      fontSize: "2rem",
      fontWeight: "bold",
      letterSpacing: "0.4em",
      color: "#c9a96e",
      margin: 0,
    },
    subtitle: {
      fontSize: "0.65rem",
      letterSpacing: "0.25em",
      color: "#8a7a62",
      textTransform: "uppercase",
      marginTop: 2,
    },
    statusBar: {
      display: "flex",
      justifyContent: "center",
      alignItems: "center",
      gap: "16px",
      padding: "10px 16px",
      width: "100%",
      maxWidth: 420,
      flexWrap: "wrap",
    },
    playerIndicator: (active) => ({
      display: "flex",
      alignItems: "center",
      gap: 6,
      padding: "4px 12px",
      borderRadius: 6,
      background: active ? "rgba(201,169,110,0.15)" : "transparent",
      border: active ? "1px solid #c9a96e" : "1px solid transparent",
      transition: "all 0.2s",
    }),
    stone: (color, size = 16) => ({
      width: size,
      height: size,
      borderRadius: "50%",
      background: color === "red"
        ? "radial-gradient(circle at 35% 35%, #e86050, #8b1a1a)"
        : "radial-gradient(circle at 35% 35%, #5b9bd5, #1a3a6b)",
      border: color === "red" ? "1px solid #8b1a1a" : "1px solid #1a3a6b",
      boxShadow: "0 1px 3px rgba(0,0,0,0.4)",
      flexShrink: 0,
    }),
    stoneCount: {
      fontSize: "0.85rem",
      color: "#b0a48e",
    },
    boardArea: {
      flex: 1,
      display: "flex",
      justifyContent: "center",
      alignItems: "center",
      width: "100%",
      padding: "4px",
      overflow: "hidden",
    },
    controls: {
      display: "flex",
      gap: 8,
      padding: "8px 16px 6px",
      flexWrap: "wrap",
      justifyContent: "center",
      width: "100%",
      maxWidth: 420,
    },
    btn: (variant) => ({
      padding: "8px 16px",
      borderRadius: 6,
      border: variant === "primary"
        ? "1px solid #c9a96e"
        : variant === "danger"
        ? "1px solid #a05a3a"
        : "1px solid #5a5046",
      background: variant === "primary"
        ? "rgba(201,169,110,0.2)"
        : variant === "danger"
        ? "rgba(160,90,58,0.15)"
        : "rgba(90,80,70,0.15)",
      color: variant === "primary"
        ? "#c9a96e"
        : variant === "danger"
        ? "#d08060"
        : "#b0a48e",
      fontSize: "0.8rem",
      fontFamily: "'Courier New', monospace",
      cursor: "pointer",
      letterSpacing: "0.05em",
      fontWeight: "bold",
      textTransform: "uppercase",
    }),
    error: {
      color: "#d08060",
      fontSize: "0.75rem",
      textAlign: "center",
      padding: "2px 16px",
      minHeight: 18,
    },
    passMsg: {
      color: "#8a7a62",
      fontSize: "0.75rem",
      textAlign: "center",
      padding: "2px 16px",
    },
    footer: {
      padding: "6px 16px 14px",
      display: "flex",
      justifyContent: "center",
      gap: 16,
      borderTop: "1px solid #3a3228",
      width: "100%",
    },
    modal: {
      position: "fixed",
      inset: 0,
      background: "rgba(0,0,0,0.8)",
      display: "flex",
      justifyContent: "center",
      alignItems: "center",
      zIndex: 100,
      padding: 20,
    },
    modalContent: {
      background: "#25201a",
      border: "1px solid #3a3228",
      borderRadius: 12,
      padding: "28px 24px",
      maxWidth: 380,
      width: "100%",
      maxHeight: "80vh",
      overflowY: "auto",
    },
  };

  const rulesContent = (
    <>
      <h2 style={{ color: "#c9a96e", fontSize: "1.2rem", marginTop: 0, letterSpacing: "0.2em" }}>HOW TO PLAY</h2>
      <div style={{ color: "#b0a48e", fontSize: "0.8rem", lineHeight: 1.7 }}>
        <p><strong style={{ color: "#c9a96e" }}>Goal:</strong> Capture all of your opponent's stones.</p>
        <p><strong style={{ color: "#c9a96e" }}>Placement:</strong> On your turn, place a stone of your color on an empty cell.</p>
        <p><strong style={{ color: "#c9a96e" }}>Non-capturing:</strong> A stone placed with no friendly neighbors ends your turn. You may place next to enemy stones.</p>
        <p><strong style={{ color: "#c9a96e" }}>Capturing:</strong> When your stone connects to friendly stones, the new larger group captures all adjacent enemy groups that are smaller. Captured stones are removed.</p>
        <p><strong style={{ color: "#c9a96e" }}>Continue placing:</strong> After a capture, you <em>must</em> keep placing until you make a non-capturing placement.</p>
        <p><strong style={{ color: "#c9a96e" }}>Pass:</strong> If you have no valid placements, you must pass.</p>
        <p><strong style={{ color: "#c9a96e" }}>No draws:</strong> The game always produces a winner.</p>
        <p style={{ marginTop: 8 }}><a href="https://www.marksteeregames.com/Oust_rules.pdf" target="_blank" rel="noopener noreferrer" style={{ color: "#c9a96e" }}>Full rules at marksteeregames.com</a></p>
      </div>
    </>
  );

  // ── Menu screen ──────────────────────────────────────────────────
  if (showMenu) {
    return (
      <div style={styles.container}>
        <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", padding: 24 }}>
          <h1 style={{ ...styles.title, fontSize: "3rem", letterSpacing: "0.6em", marginBottom: 4 }}>OUST</h1>
          <p style={{ ...styles.subtitle, marginBottom: 40 }}>A game by Mark Steere</p>

          <p style={{ color: "#8a7a62", fontSize: "0.8rem", marginBottom: 12, letterSpacing: "0.15em", textTransform: "uppercase" }}>Board Size</p>
          <div style={{ display: "flex", gap: 10, marginBottom: 36 }}>
            {BOARD_SIZES.map(s => (
              <button
                key={s}
                onClick={() => setBoardSize(s)}
                style={{
                  width: 44, height: 44, borderRadius: 8,
                  background: s === boardSize ? "rgba(201,169,110,0.25)" : "rgba(90,80,70,0.15)",
                  border: s === boardSize ? "2px solid #c9a96e" : "1px solid #5a5046",
                  color: s === boardSize ? "#c9a96e" : "#8a7a62",
                  fontSize: "1.1rem", fontFamily: "'Courier New', monospace",
                  fontWeight: "bold", cursor: "pointer",
                }}
              >
                {s}
              </button>
            ))}
          </div>

          <button
            onClick={() => resetGame(boardSize)}
            style={{ ...styles.btn("primary"), padding: "14px 48px", fontSize: "1rem", letterSpacing: "0.2em" }}
          >
            Start Game
          </button>

          <button
            onClick={() => setShowRules(true)}
            style={{ ...styles.btn(""), marginTop: 16, padding: "10px 32px" }}
          >
            Rules
          </button>
        </div>

        {showRules && (
          <div style={styles.modal} onClick={() => setShowRules(false)}>
            <div style={styles.modalContent} onClick={e => e.stopPropagation()}>
              {rulesContent}
              <button onClick={() => setShowRules(false)} style={{ ...styles.btn("primary"), marginTop: 16, width: "100%" }}>Got It</button>
            </div>
          </div>
        )}
      </div>
    );
  }

  // ── Game screen ──────────────────────────────────────────────────
  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <h1 style={styles.title}>OUST</h1>
        <p style={styles.subtitle}>
          {gameOver
            ? `${winner === "red" ? "Red" : "Blue"} wins!`
            : mustContinue
            ? "Capture! Continue placing..."
            : `${currentPlayer === "red" ? "Red" : "Blue"}'s turn`}
        </p>
      </div>

      {/* Status */}
      <div style={styles.statusBar}>
        <div style={styles.playerIndicator(currentPlayer === "red" && !gameOver)}>
          <div style={styles.stone("red")} />
          <span style={styles.stoneCount}>{stones.red} stone{stones.red !== 1 ? "s" : ""}</span>
        </div>
        <div style={styles.playerIndicator(currentPlayer === "blue" && !gameOver)}>
          <div style={styles.stone("blue")} />
          <span style={styles.stoneCount}>{stones.blue} stone{stones.blue !== 1 ? "s" : ""}</span>
        </div>
      </div>

      {passMessage && <div style={styles.passMsg}>{passMessage}</div>}

      {/* Board */}
      <div style={styles.boardArea}>
        <svg viewBox={viewBox} style={{ width: "100%", maxWidth: 500, maxHeight: "55vh" }}>
          <defs>
            <radialGradient id="redStone" cx="35%" cy="35%">
              <stop offset="0%" stopColor="#e86050" />
              <stop offset="100%" stopColor="#8b1a1a" />
            </radialGradient>
            <radialGradient id="blueStone" cx="35%" cy="35%">
              <stop offset="0%" stopColor="#5b9bd5" />
              <stop offset="100%" stopColor="#1a3a6b" />
            </radialGradient>
            <filter id="stoneShadow">
              <feDropShadow dx="0" dy="1" stdDeviation="1.5" floodColor="#000" floodOpacity="0.4" />
            </filter>
            <filter id="glow">
              <feGaussianBlur stdDeviation="2" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {cells.map(({ q, r }) => {
            const { x, y } = hexToPixel(q, r);
            const k = key(q, r);
            const stoneColor = board.get(k);
            const isEmpty = !stoneColor;
            const isValid = isEmpty && !gameOver && validSet.has(k);
            const isPlacedThisTurn = lastPlacedKeys.has(k);

            return (
              <g key={k} onClick={() => isValid && handleCellClick(q, r)} style={{ cursor: isValid ? "pointer" : "default" }}>
                <polygon
                  points={hexPoints(x, y, HEX_SIZE - 1)}
                  fill={isEmpty ? "#2a2420" : "transparent"}
                  stroke="#3d352b"
                  strokeWidth={0.8}
                />
                {isValid && (
                  <polygon
                    points={hexPoints(x, y, HEX_SIZE - 1)}
                    fill="transparent"
                    stroke="transparent"
                    onMouseEnter={e => { e.target.style.fill = "rgba(201,169,110,0.08)"; }}
                    onMouseLeave={e => { e.target.style.fill = "transparent"; }}
                  />
                )}
                {/* Valid placement dot */}
                {isValid && (
                  <circle
                    cx={x} cy={y}
                    r={HEX_SIZE * 0.15}
                    fill={currentPlayer === "red" ? "#e86050" : "#5b9bd5"}
                    opacity={0.35}
                  />
                )}
                {/* Stone */}
                {stoneColor && (
                  <circle
                    cx={x} cy={y}
                    r={HEX_SIZE * 0.55}
                    fill={`url(#${stoneColor}Stone)`}
                    stroke={stoneColor === "red" ? "#8b1a1a" : "#1a3a6b"}
                    strokeWidth={0.5}
                    filter="url(#stoneShadow)"
                  />
                )}
                {/* Glow for stones placed this turn */}
                {isPlacedThisTurn && stoneColor && (
                  <circle
                    cx={x} cy={y}
                    r={HEX_SIZE * 0.65}
                    fill="none"
                    stroke="#c9a96e"
                    strokeWidth={1.5}
                    opacity={0.6}
                    filter="url(#glow)"
                  />
                )}
              </g>
            );
          })}
        </svg>
      </div>

      {/* Error */}
      <div style={styles.error}>{errorMsg}</div>

      {/* Controls */}
      {!gameOver && turnHistory.length > 0 && (
        <div style={styles.controls}>
          <button style={styles.btn("")} onClick={undoLastPlacement}>Undo</button>
        </div>
      )}

      {/* Game Over */}
      {gameOver && (
        <div style={{ textAlign: "center", padding: "12px 16px" }}>
          <div style={{ display: "flex", justifyContent: "center", gap: 24, marginBottom: 16 }}>
            <div>
              <div style={styles.stone("red", 24)} />
              <div style={{ color: winner === "red" ? "#c9a96e" : "#8a7a62", fontWeight: winner === "red" ? "bold" : "normal", marginTop: 4 }}>
                {stones.red} stone{stones.red !== 1 ? "s" : ""}
              </div>
            </div>
            <div>
              <div style={styles.stone("blue", 24)} />
              <div style={{ color: winner === "blue" ? "#c9a96e" : "#8a7a62", fontWeight: winner === "blue" ? "bold" : "normal", marginTop: 4 }}>
                {stones.blue} stone{stones.blue !== 1 ? "s" : ""}
              </div>
            </div>
          </div>
          <button style={{ ...styles.btn("primary"), padding: "12px 40px" }} onClick={() => setShowMenu(true)}>
            New Game
          </button>
        </div>
      )}

      {/* Footer */}
      <div style={styles.footer}>
        <button style={{ ...styles.btn(""), fontSize: "0.7rem", padding: "4px 12px" }} onClick={() => setShowRules(true)}>
          Rules
        </button>
        <button style={{ ...styles.btn("danger"), fontSize: "0.7rem", padding: "4px 12px" }} onClick={() => setShowMenu(true)}>
          Quit
        </button>
      </div>

      {/* Rules modal */}
      {showRules && (
        <div style={styles.modal} onClick={() => setShowRules(false)}>
          <div style={styles.modalContent} onClick={e => e.stopPropagation()}>
            {rulesContent}
            <button onClick={() => setShowRules(false)} style={{ ...styles.btn("primary"), marginTop: 16, width: "100%" }}>Got It</button>
          </div>
        </div>
      )}
    </div>
  );
}

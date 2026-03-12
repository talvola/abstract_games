import { useState, useCallback, useMemo, useEffect } from "react";

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
      if (Math.abs(q + r) <= size - 1) {
        cells.push({ q, r });
      }
    }
  }
  return cells;
}

function key(q, r) { return `${q},${r}`; }

function countGroups(board) {
  const visited = new Set();
  let black = 0, white = 0;
  for (const [k, color] of board.entries()) {
    if (visited.has(k)) continue;
    // BFS
    const queue = [k];
    visited.add(k);
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
    if (color === "black") black++;
    else white++;
  }
  return { black, white, total: black + white };
}

// ── Hex rendering helpers ──────────────────────────────────────────
const HEX_SIZE = 28;
const SQRT3 = Math.sqrt(3);

function hexToPixel(q, r) {
  const x = HEX_SIZE * (SQRT3 * q + (SQRT3 / 2) * r);
  const y = HEX_SIZE * (1.5 * r);
  return { x, y };
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

export default function YoddGame() {
  const [boardSize, setBoardSize] = useState(6);
  const [board, setBoard] = useState(new Map());
  const [currentPlayer, setCurrentPlayer] = useState("black"); // "black" | "white"
  const [turnNumber, setTurnNumber] = useState(1);
  const [stonesPlacedThisTurn, setStonesPlacedThisTurn] = useState([]);
  const [placingColor, setPlacingColor] = useState("black");
  const [gameOver, setGameOver] = useState(false);
  const [passCount, setPassCount] = useState(0);
  const [winner, setWinner] = useState(null);
  const [boardBeforeTurn, setBoardBeforeTurn] = useState(new Map());
  const [showRules, setShowRules] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [showMenu, setShowMenu] = useState(true);

  const cells = useMemo(() => generateHexGrid(boardSize), [boardSize]);

  const maxStones = turnNumber === 1 && currentPlayer === "black" ? 1 : 2;

  const groups = useMemo(() => countGroups(board), [board]);

  // check if current placement is valid (odd total groups)
  const isOddGroups = groups.total % 2 === 1;

  function resetGame(size) {
    setBoardSize(size || boardSize);
    setBoard(new Map());
    setCurrentPlayer("black");
    setTurnNumber(1);
    setStonesPlacedThisTurn([]);
    setPlacingColor("black");
    setGameOver(false);
    setPassCount(0);
    setWinner(null);
    setBoardBeforeTurn(new Map());
    setErrorMsg("");
    setShowMenu(false);
  }

  function handleCellClick(q, r) {
    if (gameOver) return;
    const k = key(q, r);

    // If cell occupied, ignore
    if (board.has(k)) return;

    // Check stone limit
    if (stonesPlacedThisTurn.length >= maxStones) {
      setErrorMsg(`You can only place ${maxStones} stone${maxStones > 1 ? "s" : ""} this turn.`);
      return;
    }

    // Save board state before first placement this turn
    if (stonesPlacedThisTurn.length === 0) {
      setBoardBeforeTurn(new Map(board));
    }

    const newBoard = new Map(board);
    newBoard.set(k, placingColor);
    setBoard(newBoard);
    setStonesPlacedThisTurn([...stonesPlacedThisTurn, { q, r, color: placingColor }]);
    setPassCount(0);
    setErrorMsg("");
  }

  function undoLastStone() {
    if (stonesPlacedThisTurn.length === 0) return;
    const last = stonesPlacedThisTurn[stonesPlacedThisTurn.length - 1];
    const newBoard = new Map(board);
    newBoard.delete(key(last.q, last.r));
    setBoard(newBoard);
    setStonesPlacedThisTurn(stonesPlacedThisTurn.slice(0, -1));
    setErrorMsg("");
  }

  function confirmTurn() {
    if (stonesPlacedThisTurn.length === 0) {
      setErrorMsg("Place at least one stone, or pass.");
      return;
    }
    // Validate odd groups
    if (!isOddGroups) {
      setErrorMsg("Total groups must be odd! Adjust your placement.");
      return;
    }
    // Commit turn
    setCurrentPlayer(currentPlayer === "black" ? "white" : "black");
    setTurnNumber(turnNumber + 1);
    setStonesPlacedThisTurn([]);
    setPlacingColor(currentPlayer === "black" ? "white" : "black");
    setBoardBeforeTurn(new Map(board));
    setPassCount(0);
    setErrorMsg("");
  }

  function handlePass() {
    if (gameOver) return;
    // Can't pass if it would violate odd rule (first move)
    if (turnNumber === 1 && currentPlayer === "black") {
      setErrorMsg("Black must place a stone on the first turn.");
      return;
    }
    // If stones placed, undo them first
    if (stonesPlacedThisTurn.length > 0) {
      setBoard(boardBeforeTurn);
      setStonesPlacedThisTurn([]);
    }
    // Check passing is valid - groups must still be odd (or board is empty which is 0, even)
    // Passing means no change to board, so current group count must be odd
    const currentGroups = countGroups(boardBeforeTurn.size > 0 ? boardBeforeTurn : board);
    if (currentGroups.total > 0 && currentGroups.total % 2 !== 1) {
      setErrorMsg("Can't pass — total groups would not be odd.");
      return;
    }

    const newPassCount = passCount + 1;
    if (newPassCount >= 2) {
      // Game over
      const finalGroups = countGroups(board);
      setGameOver(true);
      if (finalGroups.black < finalGroups.white) setWinner("black");
      else if (finalGroups.white < finalGroups.black) setWinner("white");
      else setWinner("draw");
      return;
    }
    setPassCount(newPassCount);
    setCurrentPlayer(currentPlayer === "black" ? "white" : "black");
    setTurnNumber(turnNumber + 1);
    setStonesPlacedThisTurn([]);
    setPlacingColor(currentPlayer === "black" ? "white" : "black");
    setErrorMsg("");
  }

  function undoAllThisTurn() {
    if (stonesPlacedThisTurn.length === 0) return;
    setBoard(new Map(boardBeforeTurn));
    setStonesPlacedThisTurn([]);
    setErrorMsg("");
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
      background: color === "black"
        ? "radial-gradient(circle at 35% 35%, #555, #111)"
        : "radial-gradient(circle at 35% 35%, #fff, #bbb)",
      border: color === "black" ? "1px solid #333" : "1px solid #999",
      boxShadow: color === "black"
        ? "0 1px 3px rgba(0,0,0,0.5)"
        : "0 1px 3px rgba(0,0,0,0.3)",
      flexShrink: 0,
    }),
    groupCount: {
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
    colorPicker: {
      display: "flex",
      alignItems: "center",
      gap: 6,
      padding: "6px 16px 10px",
    },
    colorBtn: (color, active) => ({
      width: 32,
      height: 32,
      borderRadius: "50%",
      background: color === "black"
        ? "radial-gradient(circle at 35% 35%, #555, #111)"
        : "radial-gradient(circle at 35% 35%, #fff, #bbb)",
      border: active
        ? "2px solid #c9a96e"
        : color === "black"
        ? "2px solid #444"
        : "2px solid #888",
      cursor: "pointer",
      boxShadow: active ? "0 0 8px rgba(201,169,110,0.5)" : "none",
      transition: "all 0.15s",
    }),
    error: {
      color: "#d08060",
      fontSize: "0.75rem",
      textAlign: "center",
      padding: "2px 16px",
      minHeight: 18,
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

  // ── Menu screen ──────────────────────────────────────────────────
  if (showMenu) {
    return (
      <div style={styles.container}>
        <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", padding: 24 }}>
          <h1 style={{ ...styles.title, fontSize: "3rem", letterSpacing: "0.6em", marginBottom: 4 }}>YODD</h1>
          <p style={{ ...styles.subtitle, marginBottom: 40 }}>A connection game by Luis Bolaños Mures</p>

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
            style={{
              ...styles.btn("primary"),
              padding: "14px 48px",
              fontSize: "1rem",
              letterSpacing: "0.2em",
            }}
          >
            Start Game
          </button>

          <button
            onClick={() => setShowRules(true)}
            style={{
              ...styles.btn(""),
              marginTop: 16,
              padding: "10px 32px",
            }}
          >
            Rules
          </button>
        </div>

        {showRules && (
          <div style={styles.modal} onClick={() => setShowRules(false)}>
            <div style={styles.modalContent} onClick={e => e.stopPropagation()}>
              <h2 style={{ color: "#c9a96e", fontSize: "1.2rem", marginTop: 0, letterSpacing: "0.2em" }}>HOW TO PLAY</h2>
              <div style={{ color: "#b0a48e", fontSize: "0.8rem", lineHeight: 1.7 }}>
                <p><strong style={{ color: "#c9a96e" }}>Goal:</strong> Have <em>fewer</em> groups of your color when the game ends.</p>
                <p><strong style={{ color: "#c9a96e" }}>Group:</strong> A set of connected same-colored stones.</p>
                <p><strong style={{ color: "#c9a96e" }}>Turn:</strong> Place 1 or 2 stones of <em>either</em> color on empty cells. (Black's first turn: only 1 stone.)</p>
                <p><strong style={{ color: "#c9a96e" }}>The Odd Rule:</strong> After each turn, the <em>total</em> number of groups on the board must be odd.</p>
                <p><strong style={{ color: "#c9a96e" }}>Passing:</strong> You may pass instead of placing, unless it would violate the odd rule.</p>
                <p><strong style={{ color: "#c9a96e" }}>Game End:</strong> Both players pass consecutively. Fewest groups wins.</p>
                <p style={{ marginTop: 8 }}><a href="https://boardgamegeek.com/boardgame/105173/yodd" target="_blank" rel="noopener noreferrer" style={{ color: "#c9a96e" }}>More info on BoardGameGeek</a></p>
              </div>
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
        <h1 style={styles.title}>YODD</h1>
        <p style={styles.subtitle}>
          {gameOver
            ? winner === "draw" ? "Draw!" : `${winner} wins!`
            : `Turn ${turnNumber}`}
        </p>
      </div>

      {/* Status */}
      <div style={styles.statusBar}>
        <div style={styles.playerIndicator(currentPlayer === "black" && !gameOver)}>
          <div style={styles.stone("black")} />
          <span style={styles.groupCount}>{groups.black} grp{groups.black !== 1 ? "s" : ""}</span>
        </div>
        <span style={{ color: "#5a5046", fontSize: "0.7rem" }}>
          {groups.total} total {!isOddGroups && stonesPlacedThisTurn.length > 0 ? "⚠ EVEN" : ""}
        </span>
        <div style={styles.playerIndicator(currentPlayer === "white" && !gameOver)}>
          <div style={styles.stone("white")} />
          <span style={styles.groupCount}>{groups.white} grp{groups.white !== 1 ? "s" : ""}</span>
        </div>
      </div>

      {/* Board */}
      <div style={styles.boardArea}>
        <svg viewBox={viewBox} style={{ width: "100%", maxWidth: 500, maxHeight: "55vh" }}>
          <defs>
            <radialGradient id="blackStone" cx="35%" cy="35%">
              <stop offset="0%" stopColor="#666" />
              <stop offset="100%" stopColor="#111" />
            </radialGradient>
            <radialGradient id="whiteStone" cx="35%" cy="35%">
              <stop offset="0%" stopColor="#fff" />
              <stop offset="100%" stopColor="#bbb" />
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
            const isPlacedThisTurn = stonesPlacedThisTurn.some(s => s.q === q && s.r === r);
            const isEmpty = !stoneColor;

            return (
              <g key={k} onClick={() => isEmpty && !gameOver && handleCellClick(q, r)} style={{ cursor: isEmpty && !gameOver ? "pointer" : "default" }}>
                {/* Hex cell */}
                <polygon
                  points={hexPoints(x, y, HEX_SIZE - 1)}
                  fill={isEmpty ? "#2a2420" : "transparent"}
                  stroke="#3d352b"
                  strokeWidth={0.8}
                />
                {/* Hover target */}
                {isEmpty && !gameOver && (
                  <polygon
                    points={hexPoints(x, y, HEX_SIZE - 1)}
                    fill="transparent"
                    stroke="transparent"
                    strokeWidth={0}
                    onMouseEnter={e => { e.target.style.fill = "rgba(201,169,110,0.08)"; }}
                    onMouseLeave={e => { e.target.style.fill = "transparent"; }}
                  />
                )}
                {/* Stone */}
                {stoneColor && (
                  <circle
                    cx={x}
                    cy={y}
                    r={HEX_SIZE * 0.55}
                    fill={`url(#${stoneColor}Stone)`}
                    stroke={stoneColor === "black" ? "#333" : "#999"}
                    strokeWidth={0.5}
                    filter="url(#stoneShadow)"
                    opacity={isPlacedThisTurn ? 0.9 : 1}
                  />
                )}
                {/* Glow ring for stones placed this turn */}
                {isPlacedThisTurn && (
                  <circle
                    cx={x}
                    cy={y}
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

      {!gameOver && (
        <>
          {/* Color Picker */}
          <div style={styles.colorPicker}>
            <span style={{ fontSize: "0.7rem", color: "#8a7a62", letterSpacing: "0.1em", textTransform: "uppercase", marginRight: 4 }}>
              Place:
            </span>
            <button style={styles.colorBtn("black", placingColor === "black")} onClick={() => setPlacingColor("black")} />
            <button style={styles.colorBtn("white", placingColor === "white")} onClick={() => setPlacingColor("white")} />
            <span style={{ fontSize: "0.7rem", color: "#5a5046", marginLeft: 8 }}>
              {stonesPlacedThisTurn.length}/{maxStones}
            </span>
          </div>

          {/* Controls */}
          <div style={styles.controls}>
            {stonesPlacedThisTurn.length > 0 && (
              <button style={styles.btn("")} onClick={undoLastStone}>Undo</button>
            )}
            {stonesPlacedThisTurn.length > 0 && (
              <button style={styles.btn("primary")} onClick={confirmTurn}>
                Confirm {isOddGroups ? "✓" : ""}
              </button>
            )}
            <button style={styles.btn("")} onClick={handlePass}>Pass</button>
          </div>
        </>
      )}

      {/* Game Over */}
      {gameOver && (
        <div style={{ textAlign: "center", padding: "12px 16px" }}>
          <div style={{ display: "flex", justifyContent: "center", gap: 24, marginBottom: 16 }}>
            <div>
              <div style={styles.stone("black", 24)} />
              <div style={{ color: winner === "black" ? "#c9a96e" : "#8a7a62", fontWeight: winner === "black" ? "bold" : "normal", marginTop: 4 }}>
                {groups.black} group{groups.black !== 1 ? "s" : ""}
              </div>
            </div>
            <div>
              <div style={styles.stone("white", 24)} />
              <div style={{ color: winner === "white" ? "#c9a96e" : "#8a7a62", fontWeight: winner === "white" ? "bold" : "normal", marginTop: 4 }}>
                {groups.white} group{groups.white !== 1 ? "s" : ""}
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
            <h2 style={{ color: "#c9a96e", fontSize: "1.2rem", marginTop: 0, letterSpacing: "0.2em" }}>HOW TO PLAY</h2>
            <div style={{ color: "#b0a48e", fontSize: "0.8rem", lineHeight: 1.7 }}>
              <p><strong style={{ color: "#c9a96e" }}>Goal:</strong> Have <em>fewer</em> groups of your color when the game ends.</p>
              <p><strong style={{ color: "#c9a96e" }}>Group:</strong> A set of connected same-colored stones.</p>
              <p><strong style={{ color: "#c9a96e" }}>Turn:</strong> Place 1 or 2 stones of <em>either</em> color on empty cells. (Black's first turn: only 1 stone.)</p>
              <p><strong style={{ color: "#c9a96e" }}>The Odd Rule:</strong> After each turn, the <em>total</em> number of groups on the board must be odd.</p>
              <p><strong style={{ color: "#c9a96e" }}>Passing:</strong> You may pass instead of placing, unless it would violate the odd rule.</p>
              <p><strong style={{ color: "#c9a96e" }}>Game End:</strong> Both players pass consecutively. Fewest groups wins.</p>
              <p style={{ marginTop: 8 }}><a href="https://boardgamegeek.com/boardgame/105173/yodd" target="_blank" rel="noopener noreferrer" style={{ color: "#c9a96e" }}>More info on BoardGameGeek</a></p>
            </div>
            <button onClick={() => setShowRules(false)} style={{ ...styles.btn("primary"), marginTop: 16, width: "100%" }}>Got It</button>
          </div>
        </div>
      )}
    </div>
  );
}

// Thin wrapper over the backend. The frontend never encodes any game rules;
// it only moves opaque `state` blobs around and renders the `view` it gets back.

async function post(path, body) {
  const res = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body || {}),
  })
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}))
    throw new Error(detail.detail || `request failed: ${res.status}`)
  }
  return res.json()
}

export const api = {
  listGames: () => fetch('/api/games').then((r) => r.json()),
  newGame: (uid, options) => post(`/api/games/${uid}/new`, { options }),
  move: (uid, state, move) => post(`/api/games/${uid}/move`, { state, move }),
  bot: (uid, state, iterations) => post(`/api/games/${uid}/bot`, { state, iterations }),
}

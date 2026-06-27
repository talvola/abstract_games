// Thin wrapper over the backend. The frontend never encodes any game rules;
// it only moves opaque `state` blobs around and renders the `view` it gets back.
// Correspondence calls rely on the session cookie (same-origin via the dev proxy).

async function req(method, path, body) {
  const opts = { method, headers: {}, credentials: 'same-origin' }
  if (body !== undefined) {
    opts.headers['Content-Type'] = 'application/json'
    opts.body = JSON.stringify(body)
  }
  const res = await fetch(path, opts)
  if (res.status === 204) return null
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.detail || `request failed: ${res.status}`)
  return data
}

const get = (p) => req('GET', p)
const post = (p, b) => req('POST', p, b ?? {})
const del = (p) => req('DELETE', p)

export const api = {
  // catalogue
  listGames: () => get('/api/games'),
  gameRules: (uid) => get(`/api/games/${uid}/rules`),

  // auth
  me: () => get('/api/auth/me'),
  register: (email, display_name, password) =>
    post('/api/auth/register', { email, display_name, password }),
  login: (email, password) => post('/api/auth/login', { email, password }),
  logout: () => post('/api/auth/logout'),

  // correspondence
  seeks: () => get('/api/seeks'),
  createSeek: (game_uid, options, seat_pref) =>
    post('/api/seeks', { game_uid, options, seat_pref }),
  acceptSeek: (id) => post(`/api/seeks/${id}/accept`),
  cancelSeek: (id) => del(`/api/seeks/${id}`),
  quickPair: (game_uid, options) => post('/api/quickpair', { game_uid, options }),
  newBotMatch: (game_uid, options, seat, bot_iterations) =>
    post('/api/matches', { game_uid, options, opponent: 'bot', seat, bot_iterations }),
  myMatches: () => get('/api/matches'),
  getMatch: (id) => get(`/api/matches/${id}`),
  matchMove: (id, move) => post(`/api/matches/${id}/move`, { move }),
  advanceMatch: (id) => post(`/api/matches/${id}/advance`),
  resignMatch: (id) => post(`/api/matches/${id}/resign`),
  deleteMatch: (id) => del(`/api/matches/${id}`),

  // ratings
  leaderboard: (uid) => get(`/api/leaderboard/${uid}`),
  userProfile: (id) => get(`/api/users/${id}`),
  matchReplay: (id) => get(`/api/matches/${id}/replay`),

  // upload a game package (.zip)
  uploadGame: async (file) => {
    const fd = new FormData()
    fd.append('file', file)
    const res = await fetch('/api/games/upload', { method: 'POST', body: fd, credentials: 'same-origin' })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(data.detail || `upload failed: ${res.status}`)
    return data
  },

  // stateless quick-play (no login)
  newGame: (uid, options) => post(`/api/games/${uid}/new`, { options }),
  move: (uid, state, move) => post(`/api/games/${uid}/move`, { state, move }),
  bot: (uid, state, iterations) => post(`/api/games/${uid}/bot`, { state, iterations }),
}

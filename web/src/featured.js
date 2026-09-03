// Curated "Start here" shelf shown at the top of the game browser when nobody
// is searching or filtering. Order matters (classics first, then the modern
// standards). A uid that isn't in the registry is silently skipped, so this
// list can be edited freely. Site curation, not game metadata — which is why it
// lives here and not in the manifests.
export const FEATURED = [
  'chess',
  'go',
  'checkers',
  'reversi',
  'backgammon',
  'connect_four',
  'nine_mens_morris',
  'hex',
  'hive',
  'tak',
  'santorini',
  'onitama',
  'quoridor',
  'abalone',
  'arimaa',
  'yinsh',
]

// What the pickers select before the visitor chooses anything.
export const DEFAULT_GAME = 'chess'

export function defaultGameUid(games) {
  return games.some((g) => g.uid === DEFAULT_GAME) ? DEFAULT_GAME : games[0]?.uid
}

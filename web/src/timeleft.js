// Human "time remaining" from an ISO deadline, shared by the lobby + match screen.
export function timeLeft(iso) {
  const ms = new Date(iso) - new Date()
  if (ms <= 0) return 'overdue'
  const h = ms / 3600000
  if (h >= 48) return `${Math.round(h / 24)}d left`
  if (h >= 1) return `${Math.round(h)}h left`
  return `${Math.max(1, Math.round(ms / 60000))}m left`
}

export const deadlineUrgent = (iso) => new Date(iso) - new Date() < 24 * 3600000

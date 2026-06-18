// Minimal, XSS-safe Markdown -> React renderer for rules pages. Supports headings
// (#/##/###), paragraphs, -/* and 1. lists, and inline **bold**, *italic*,
// `code`, [links](url). No raw HTML is ever injected.

function inline(text) {
  const out = []
  const re = /(\*\*([^*]+)\*\*)|(\*([^*]+)\*)|(`([^`]+)`)|(\[([^\]]+)\]\(([^)]+)\))/g
  let last = 0, m, k = 0
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(text.slice(last, m.index))
    if (m[1]) out.push(<strong key={k++}>{m[2]}</strong>)
    else if (m[3]) out.push(<em key={k++}>{m[4]}</em>)
    else if (m[5]) out.push(<code key={k++}>{m[6]}</code>)
    else if (m[7]) out.push(<a key={k++} href={m[9]} target="_blank" rel="noopener noreferrer">{m[8]}</a>)
    last = re.lastIndex
  }
  if (last < text.length) out.push(text.slice(last))
  return out
}

const isBlock = (l) => /^(#{1,3}\s|[-*]\s|\d+\.\s)/.test(l.trimStart())

export default function Markdown({ text }) {
  const lines = (text || '').replace(/\r\n/g, '\n').split('\n')
  const blocks = []
  let i = 0
  while (i < lines.length) {
    const line = lines[i]
    if (/^\s*$/.test(line)) { i++; continue }
    const h = /^(#{1,3})\s+(.*)$/.exec(line)
    if (h) {
      const Tag = `h${h[1].length}`
      blocks.push(<Tag key={blocks.length}>{inline(h[2])}</Tag>)
      i++
    } else if (/^\s*[-*]\s+/.test(line)) {
      const items = []
      while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) {
        items.push(<li key={items.length}>{inline(lines[i].replace(/^\s*[-*]\s+/, ''))}</li>); i++
      }
      blocks.push(<ul key={blocks.length}>{items}</ul>)
    } else if (/^\s*\d+\.\s+/.test(line)) {
      const items = []
      while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i])) {
        items.push(<li key={items.length}>{inline(lines[i].replace(/^\s*\d+\.\s+/, ''))}</li>); i++
      }
      blocks.push(<ol key={blocks.length}>{items}</ol>)
    } else {
      const buf = []
      while (i < lines.length && !/^\s*$/.test(lines[i]) && !isBlock(lines[i])) {
        buf.push(lines[i]); i++
      }
      blocks.push(<p key={blocks.length}>{inline(buf.join(' '))}</p>)
    }
  }
  return <div className="markdown">{blocks}</div>
}

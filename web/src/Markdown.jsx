// Minimal, XSS-safe Markdown -> React renderer for rules pages. Supports headings
// (#/##/###), paragraphs, -/* and 1. lists, ``` fenced code blocks, GFM pipe
// tables, and inline **bold**, *italic*, `code`, [links](url). No raw HTML is
// ever injected.

// Inline spans. Two things beyond the obvious, both of which shipped broken and
// showed the reader raw asterisks in 44 of the library's rules.md files:
//   * NESTED emphasis — "**a quint of *your* colour**". The old pattern used
//     [^*]+ inside **…**, so any inner "*" made the whole span fail to match.
//     Bold now accepts single (non-"**") asterisks and re-parses its content,
//     which terminates because the inner text is strictly shorter.
//   * BACKSLASH ESCAPES — "\*Star" (a real game name) and "f8\*D". Consumed
//     FIRST, so an escaped asterisk can never act as a delimiter.
// Code spans are matched but NOT re-parsed, so their contents stay literal.
function inline(text) {
  const out = []
  const re = /\\([\\*_`[\]|])|(\*\*\*([^*]+)\*\*\*)|(\*\*((?:[^*]|\*(?!\*))+?)\*\*)|(\*([^*]+?)\*)|(`([^`]+)`)|(\[([^\]]+)\]\(([^)]+)\))/g
  let last = 0, m, k = 0
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(text.slice(last, m.index))
    if (m[1]) out.push(m[1])                                    // escaped literal char
    else if (m[2]) out.push(<strong key={k++}><em>{m[3]}</em></strong>)   // ***both***
    else if (m[4]) out.push(<strong key={k++}>{inline(m[5])}</strong>)
    else if (m[6]) out.push(<em key={k++}>{inline(m[7])}</em>)
    else if (m[8]) out.push(<code key={k++}>{m[9]}</code>)
    else if (m[10]) {
      const url = m[12].trim()
      const href = /^(https?:|mailto:|\/|#)/i.test(url) ? url : '#'  // block javascript:/data:/etc.
      out.push(<a key={k++} href={href} target="_blank" rel="noopener noreferrer">{inline(m[11])}</a>)
    }
    last = re.lastIndex
  }
  if (last < text.length) out.push(text.slice(last))
  return out
}

// Split one table row on its unescaped "|" separators, dropping the empty cells
// the leading/trailing pipes produce. Hand-rolled rather than a regex so that a
// cell may contain a literal pipe as "\|" (Trax names a tile `\|`).
function splitRow(line) {
  const cells = []
  let cur = ''
  for (let i = 0; i < line.length; i++) {
    if (line[i] === '\\' && line[i + 1] === '|') { cur += '|'; i++ }
    else if (line[i] === '|') { cells.push(cur); cur = '' }
    else cur += line[i]
  }
  cells.push(cur)
  if (cells.length && !cells[0].trim()) cells.shift()
  if (cells.length && !cells[cells.length - 1].trim()) cells.pop()
  return cells.map((c) => c.trim())
}

// A GFM table separator: every cell is ---, :---, ---: or :---:.
function alignments(line) {
  if (!line || line.indexOf('|') < 0) return null
  const cells = splitRow(line)
  if (!cells.length || !cells.every((c) => /^:?-+:?$/.test(c))) return null
  return cells.map((c) => (c.startsWith(':') && c.endsWith(':') ? 'center'
    : c.endsWith(':') ? 'right' : c.startsWith(':') ? 'left' : null))
}

const isFence = (l) => /^\s*```/.test(l)
const isQuote = (l) => /^\s*>\s?/.test(l)
const isBlock = (l) => /^(#{1,3}\s|[-*]\s|\d+\.\s)/.test(l.trimStart()) || isFence(l) || isQuote(l)

export default function Markdown({ text }) {
  const lines = (text || '').replace(/\r\n/g, '\n').split('\n')
  const blocks = []
  let i = 0
  while (i < lines.length) {
    const line = lines[i]
    if (/^\s*$/.test(line)) { i++; continue }
    // Fenced code block FIRST, so list/table syntax inside a fence stays literal.
    // Rules pages use these for ASCII board diagrams, where the line breaks and
    // the column alignment ARE the content -- the paragraph branch below would
    // join them with spaces and destroy the diagram.
    if (isFence(line)) {
      const body = []
      i++
      while (i < lines.length && !isFence(lines[i])) { body.push(lines[i]); i++ }
      i++                                    // consume the closing fence (if any)
      blocks.push(<pre key={blocks.length}><code>{body.join('\n')}</code></pre>)
      continue
    }
    // GFM pipe table: a header row whose NEXT line is a --- separator.
    const aligns = line.indexOf('|') >= 0 ? alignments(lines[i + 1]) : null
    if (aligns) {
      const head = splitRow(line)
      i += 2
      const rows = []
      while (i < lines.length && lines[i].indexOf('|') >= 0 && !/^\s*$/.test(lines[i])) {
        rows.push(splitRow(lines[i])); i++
      }
      const al = (c) => (aligns[c] ? { textAlign: aligns[c] } : undefined)
      blocks.push(
        <div className="table-wrap" key={blocks.length}>
          <table>
            <thead><tr>{head.map((c, n) => <th key={n} style={al(n)}>{inline(c)}</th>)}</tr></thead>
            <tbody>{rows.map((r, n) => (
              <tr key={n}>{r.map((c, m) => <td key={m} style={al(m)}>{inline(c)}</td>)}</tr>
            ))}</tbody>
          </table>
        </div>)
      continue
    }
    if (isQuote(line)) {
      const buf = []
      while (i < lines.length && isQuote(lines[i])) {
        buf.push(lines[i].replace(/^\s*>\s?/, '')); i++
      }
      blocks.push(<blockquote key={blocks.length}>{inline(buf.join(' '))}</blockquote>)
      continue
    }
    const h = /^(#{1,3})\s+(.*)$/.exec(line)
    if (h) {
      const Tag = `h${h[1].length}`
      blocks.push(<Tag key={blocks.length}>{inline(h[2])}</Tag>)
      i++
    } else if (/^\s*[-*]\s+/.test(line) || /^\s*\d+\.\s+/.test(line)) {
      const ordered = !/^\s*[-*]\s+/.test(line)
      const marker = ordered ? /^\s*\d+\.\s+/ : /^\s*[-*]\s+/
      const items = []
      while (i < lines.length && marker.test(lines[i])) {
        // Absorb "lazy continuation" lines -- a wrapped item whose later lines
        // carry no marker. Without this a hard-wrapped bullet is torn in half,
        // its tail rendered as a separate paragraph outside the list.
        const buf = [lines[i].replace(marker, '')]
        i++
        while (i < lines.length && !/^\s*$/.test(lines[i]) && !isBlock(lines[i])
               && !(lines[i].indexOf('|') >= 0 && alignments(lines[i + 1]))) {
          buf.push(lines[i].trim()); i++
        }
        items.push(<li key={items.length}>{inline(buf.join(' '))}</li>)
      }
      const Tag = ordered ? 'ol' : 'ul'
      blocks.push(<Tag key={blocks.length}>{items}</Tag>)
    } else {
      const buf = []
      // Stop at a blank line, another block, or a table header (whose giveaway is
      // the separator on the FOLLOWING line) -- otherwise a table butted straight
      // up against a paragraph would be swallowed into it.
      while (i < lines.length && !/^\s*$/.test(lines[i]) && !isBlock(lines[i])
             && !(lines[i].indexOf('|') >= 0 && alignments(lines[i + 1]))) {
        buf.push(lines[i]); i++
      }
      blocks.push(<p key={blocks.length}>{inline(buf.join(' '))}</p>)
    }
  }
  return <div className="markdown">{blocks}</div>
}

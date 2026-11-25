export type FountainElement =
  | { type: 'scene'; text: string }
  | { type: 'action'; text: string }
  | { type: 'character'; text: string }
  | { type: 'parenthetical'; text: string }
  | { type: 'dialogue'; text: string }
  | { type: 'transition'; text: string }
  | { type: 'centered'; text: string }
  | { type: 'section'; text: string }
  | { type: 'note'; text: string }
  | { type: 'break' }

export type FountainScript = {
  title: { key: string; value: string }[]
  elements: FountainElement[]
}

const SCENE = /^(?:\.(?!\.)|(?:INT|EXT|EST|INT\.?\/EXT|I\/E)[ .])/i
const TRANSITION = /^[A-Z0-9 .'-]+TO:$/
const TITLE_KEY = /^([A-Za-z][A-Za-z ]*):\s*(.*)$/
const NOTE = /^\[\[(.*)\]\]$/
const BREAK = /^={3,}$/

function isCharacter(line: string, next: string | undefined): boolean {
  if (line.startsWith('@')) return true
  if (next === undefined || next.trim() === '') return false
  const name = line
    .replace(/\s*\(.*\)\s*$/, '')
    .replace(/\^$/, '')
    .trim()
  return name.length > 0 && /[A-Z]/.test(name) && name === name.toUpperCase()
}

function readTitle(lines: string[]): {
  title: FountainScript['title']
  rest: number
} {
  const title: FountainScript['title'] = []
  if (!TITLE_KEY.test(lines[0] ?? '')) return { title, rest: 0 }
  let index = 0
  while (index < lines.length && lines[index].trim() !== '') {
    const match = TITLE_KEY.exec(lines[index])
    if (match) title.push({ key: match[1].trim(), value: match[2].trim() })
    else if (title.length > 0) {
      const lastEntry = title[title.length - 1]
      lastEntry.value = [lastEntry.value, lines[index].trim()]
        .filter(Boolean)
        .join('\n')
    }
    index += 1
  }
  return { title, rest: index }
}

export function parseFountain(source: string): FountainScript {
  const lines = source.replace(/\r\n?/g, '\n').split('\n')
  const { title, rest } = readTitle(lines)
  const elements: FountainElement[] = []
  let index = rest
  while (index < lines.length) {
    const raw = lines[index]
    const line = raw.trim()
    if (line === '') {
      index += 1
      continue
    }
    const previousBlank = index === 0 || lines[index - 1].trim() === ''
    if (BREAK.test(line)) {
      elements.push({ type: 'break' })
    } else if (NOTE.test(line)) {
      elements.push({ type: 'note', text: NOTE.exec(line)?.[1] ?? '' })
    } else if (line.startsWith('#')) {
      elements.push({ type: 'section', text: line.replace(/^#+\s*/, '') })
    } else if (line.startsWith('=')) {
      elements.push({ type: 'note', text: line.replace(/^=\s*/, '') })
    } else if (line.startsWith('>') && line.endsWith('<')) {
      elements.push({ type: 'centered', text: line.slice(1, -1).trim() })
    } else if (line.startsWith('>')) {
      elements.push({ type: 'transition', text: line.slice(1).trim() })
    } else if (previousBlank && SCENE.test(line)) {
      elements.push({ type: 'scene', text: line.replace(/^\./, '') })
    } else if (previousBlank && TRANSITION.test(line)) {
      elements.push({ type: 'transition', text: line })
    } else if (
      previousBlank &&
      !line.startsWith('!') &&
      isCharacter(line, lines[index + 1])
    ) {
      elements.push({ type: 'character', text: line.replace(/^@/, '') })
      index += 1
      while (index < lines.length && lines[index].trim() !== '') {
        const spoken = lines[index].trim()
        if (spoken.startsWith('(') && spoken.endsWith(')'))
          elements.push({ type: 'parenthetical', text: spoken })
        else {
          const lastElement = elements[elements.length - 1]
          if (lastElement.type === 'dialogue')
            lastElement.text = `${lastElement.text}\n${spoken}`
          else elements.push({ type: 'dialogue', text: spoken })
        }
        index += 1
      }
      continue
    } else {
      const text = line.replace(/^!/, '')
      const lastElement = elements[elements.length - 1]
      if (!previousBlank && lastElement?.type === 'action')
        lastElement.text = `${lastElement.text}\n${text}`
      else elements.push({ type: 'action', text })
    }
    index += 1
  }
  return { title, elements }
}

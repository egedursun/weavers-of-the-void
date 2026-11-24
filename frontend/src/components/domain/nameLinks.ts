import { type EntryKind } from '@/components/layout/entry/entryStack'

export type LinkTarget = {
  id: number
  name: string
  kind: EntryKind
}

type Piece = { text: string; target?: LinkTarget }

const MIN_NAME_LENGTH = 3
const ESCAPE = /[.*+?^${}()|[\]\\]/g
const THREAD_MARKER = /\[\[(?:[^\]|]*\|)?([^\]]*)\]\]/g

export function stripMarkers(text: string): string {
  return text.replace(THREAD_MARKER, '$1')
}

export function splitByNames(
  text: string,
  targets: LinkTarget[],
  linked: Set<number> = new Set()
): Piece[] {
  const usable = targets
    .filter((target) => target.name.length >= MIN_NAME_LENGTH)
    .sort((left, right) => right.name.length - left.name.length)
  if (usable.length === 0) return [{ text }]
  const byName = new Map(
    usable.map((target) => [target.name.toLowerCase(), target])
  )
  const pattern = new RegExp(
    `(${usable.map((target) => target.name.replace(ESCAPE, '\\$&')).join('|')})`,
    'gi'
  )
  const pieces: Piece[] = []
  let last = 0
  for (const match of text.matchAll(pattern)) {
    const start = match.index ?? 0
    const target = byName.get(match[0].toLowerCase())
    if (!target || linked.has(target.id)) continue
    if (start > last) pieces.push({ text: text.slice(last, start) })
    pieces.push({ text: match[0], target })
    linked.add(target.id)
    last = start + match[0].length
  }
  if (last < text.length) pieces.push({ text: text.slice(last) })
  return pieces
}

import { type DrawerKind } from '@/components/layout/drawer/drawerEntries'
import { type LinkTarget, splitByNames, stripMarkers } from './nameLinks'

export type MentionName = { id: number; name: string; kind: string }
export type MentionThread = { id: number; text: string }

export type MentionPiece =
  | { type: 'text'; text: string }
  | { type: 'link'; text: string; kind: DrawerKind; id: number }
  | { type: 'thread'; text: string; title: string }

export type MentionIndex = {
  names: ReadonlyMap<number, MentionName>
  threads: ReadonlyMap<number, MentionThread>
}

const TOKEN = /\b(son|world|thread|route|entity)#(\d+)|\(#(\d+)\)|#(\d+)/g
const THREAD_SUMMARY_CHARS = 40
const ELLIPSIS = '…'

export const MENTION_FALLBACK = {
  record: 'a record',
  son: 'a son',
  world: 'a world',
  thread: 'a story',
  route: 'a road',
} as const

const DRAWER_OF_KIND: Partial<Record<string, DrawerKind>> = {
  entity: 'entity',
  son: 'son',
  foreign_god: 'foreign-god',
  creator: 'creator',
  world: 'world-guide',
}

export function threadSummary(text: string): string {
  const clean = text.replace(/\s+/g, ' ').trim()
  const short =
    clean.length > THREAD_SUMMARY_CHARS
      ? `${clean.slice(0, THREAD_SUMMARY_CHARS).trimEnd()}${ELLIPSIS}`
      : clean
  return `"${short}"`
}

function linkOf(
  entry: MentionName | undefined,
  fallback: string
): MentionPiece {
  const kind = entry ? DRAWER_OF_KIND[entry.kind] : undefined
  if (!entry || !kind) return { type: 'text', text: fallback }
  return { type: 'link', text: entry.name, kind, id: entry.id }
}

function pushText(pieces: MentionPiece[], text: string): void {
  if (!text) return
  const last = pieces[pieces.length - 1]
  if (last?.type === 'text') last.text += text
  else pieces.push({ type: 'text', text })
}

function endsWithName(text: string, name: string): boolean {
  return text.toLowerCase().endsWith(`${name.toLowerCase()} `)
}

function startsWithName(text: string, name: string): boolean {
  return text.toLowerCase().startsWith(` ${name.toLowerCase()}`)
}

export function parseMentions(
  text: string,
  index: MentionIndex
): MentionPiece[] {
  const pieces: MentionPiece[] = []
  let cursor = 0
  let skip = 0
  for (const match of text.matchAll(TOKEN)) {
    const start = match.index ?? 0
    if (start < cursor) continue
    let before = text.slice(cursor, start)
    const [token, prefix, prefixed, parenthesised, bare] = match
    let end = start + token.length
    if (parenthesised) {
      const entry = index.names.get(Number(parenthesised))
      if (entry && endsWithName(before, entry.name)) {
        before = before.slice(0, before.length - entry.name.length - 1)
        pushText(pieces, before)
        pieces.push(linkOf(entry, entry.name))
      } else pushText(pieces, before.replace(/\s$/, ''))
      cursor = end
      continue
    }
    pushText(pieces, before)
    if (prefix === 'thread') {
      const thread = index.threads.get(Number(prefixed))
      pieces.push(
        thread
          ? {
              type: 'thread',
              text: threadSummary(thread.text),
              title: thread.text,
            }
          : { type: 'text', text: MENTION_FALLBACK.thread }
      )
    } else if (prefix === 'route') {
      pushText(pieces, MENTION_FALLBACK.route)
    } else {
      const id = Number(prefixed ?? bare)
      const entry = index.names.get(id)
      const fallback =
        prefix === 'son'
          ? MENTION_FALLBACK.son
          : prefix === 'world'
            ? MENTION_FALLBACK.world
            : MENTION_FALLBACK.record
      const piece = linkOf(entry, fallback)
      if (piece.type === 'text') pushText(pieces, piece.text)
      else pieces.push(piece)
      if (entry && startsWithName(text.slice(end), entry.name))
        skip = entry.name.length + 1
    }
    end += skip
    skip = 0
    cursor = end
  }
  pushText(pieces, text.slice(cursor))
  return pieces
}

export function parseLore(
  text: string,
  index: MentionIndex,
  targets: LinkTarget[] = [],
  selfId?: number
): MentionPiece[] {
  const clean = stripMarkers(text)
  const pieces = hasMentions(clean)
    ? parseMentions(clean, index)
    : [{ type: 'text' as const, text: clean }]
  const usable = targets.filter((target) => target.id !== selfId)
  if (usable.length === 0) return pieces
  const linked = new Set<number>()
  for (const piece of pieces) if (piece.type === 'link') linked.add(piece.id)
  return pieces.flatMap((piece): MentionPiece[] =>
    piece.type === 'text'
      ? splitByNames(piece.text, usable, linked).map((part) =>
          part.target
            ? {
                type: 'link',
                text: part.text,
                kind: part.target.kind,
                id: part.target.id,
              }
            : { type: 'text', text: part.text }
        )
      : [piece]
  )
}

const TOKEN_PROBE = new RegExp(TOKEN.source)

export function hasMentions(text: string): boolean {
  return TOKEN_PROBE.test(text)
}

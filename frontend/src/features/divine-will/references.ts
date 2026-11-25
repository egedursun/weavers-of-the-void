import { type EntryKind } from '@/components/layout/entry/entryStack'

export const REFERENCE_KINDS = [
  'node',
  'entity',
  'son',
  'foreign_god',
  'world',
  'star',
  'galaxy',
  'cluster',
  'dimension',
  'incident',
  'artifact',
] as const

export type ReferenceKind = (typeof REFERENCE_KINDS)[number]

export type Reference = { kind: ReferenceKind; id: number }

export type ReferenceTarget =
  | { type: 'entry'; kind: EntryKind; id: string | undefined; label: string }
  | { type: 'artifact'; id: number; label: string }
  | { type: 'none'; label: string }

export type NameEntry = { id: number; name: string; kind: string }

export type ReferencePiece =
  | { type: 'text'; text: string }
  | { type: 'ref'; text: string; reference: Reference }

const KIND_PATTERN = REFERENCE_KINDS.join('|')
const TOKEN = new RegExp(
  `\\b(${KIND_PATTERN})#(\\d+)\\b|(?<![\\w&/])#(\\d+)\\b`,
  'g'
)
const HREF = new RegExp(`^(?:aerona:)?(${KIND_PATTERN})[:/#](\\d+)$`)

export const REFERENCE_PROTOCOLS: readonly string[] = [
  'aerona',
  ...REFERENCE_KINDS,
]

const ENTRY_OF_KIND: Partial<Record<string, EntryKind>> = {
  entity: 'entity',
  son: 'son',
  foreign_god: 'foreign-god',
  creator: 'creator',
  world: 'world',
  star: 'star',
  galaxy: 'galaxy',
  cluster: 'cluster',
  dimension: 'dimension',
}

const FALLBACK_LABEL: Record<ReferenceKind, string> = {
  node: 'a record',
  entity: 'a record',
  son: 'a son',
  foreign_god: 'a foreign god',
  world: 'a world',
  star: 'a star',
  galaxy: 'a galaxy',
  cluster: 'a cluster',
  dimension: 'a dimension',
  incident: 'a happening',
  artifact: 'a writing',
}

function isReferenceKind(value: string): value is ReferenceKind {
  return (REFERENCE_KINDS as readonly string[]).includes(value)
}

export function splitReferences(text: string): ReferencePiece[] {
  const pieces: ReferencePiece[] = []
  let cursor = 0
  for (const match of text.matchAll(TOKEN)) {
    const start = match.index
    const [token, prefix, prefixed, bare] = match
    const kind = prefix && isReferenceKind(prefix) ? prefix : 'node'
    const id = Number(prefixed ?? bare)
    if (start > cursor)
      pieces.push({ type: 'text', text: text.slice(cursor, start) })
    pieces.push({ type: 'ref', text: token, reference: { kind, id } })
    cursor = start + token.length
  }
  if (cursor < text.length)
    pieces.push({ type: 'text', text: text.slice(cursor) })
  return pieces
}

export function referenceHref(reference: Reference): string {
  return `aerona:${reference.kind}/${String(reference.id)}`
}

export function parseReferenceHref(href: string | undefined): Reference | null {
  if (!href) return null
  const match = HREF.exec(href.trim())
  if (!match || !isReferenceKind(match[1])) return null
  return { kind: match[1], id: Number(match[2]) }
}

export function resolveReference(
  reference: Reference,
  names: ReadonlyMap<number, NameEntry>
): ReferenceTarget {
  if (reference.kind === 'artifact')
    return {
      type: 'artifact',
      id: reference.id,
      label: FALLBACK_LABEL.artifact,
    }
  if (reference.kind === 'incident')
    return {
      type: 'entry',
      kind: 'incident',
      id: String(reference.id),
      label: FALLBACK_LABEL.incident,
    }
  const named = names.get(reference.id)
  const entryKind =
    reference.kind === 'node'
      ? ENTRY_OF_KIND[named?.kind ?? '']
      : ENTRY_OF_KIND[reference.kind]
  const label = named?.name ?? FALLBACK_LABEL[reference.kind]
  if (!entryKind) return { type: 'none', label }
  return {
    type: 'entry',
    kind: entryKind,
    id: entryKind === 'creator' ? undefined : String(reference.id),
    label,
  }
}

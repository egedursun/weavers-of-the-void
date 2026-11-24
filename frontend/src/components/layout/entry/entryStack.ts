import {
  ENTRY_SEPARATOR,
  ENTRY_ID_SEPARATOR,
  MAX_ENTRY_DEPTH,
} from '@/constants/ui'

export const ENTRY_KINDS = [
  'son',
  'entity',
  'foreign-god',
  'world',
  'star',
  'galaxy',
  'cluster',
  'dimension',
  'creator',
  'world-guide',
  'help',
  'incident',
] as const

export type EntryKind = (typeof ENTRY_KINDS)[number]

export const SINGLETON_ENTRY_KINDS: ReadonlySet<EntryKind> = new Set([
  'creator',
  'help',
])

export const ENTRY_KIND_LABEL: Record<EntryKind, string> = {
  son: 'Son',
  entity: 'Record',
  'foreign-god': 'Foreign god',
  world: 'World',
  star: 'Star',
  galaxy: 'Galaxy',
  cluster: 'Cluster',
  dimension: 'Dimension',
  creator: 'Creator',
  'world-guide': "Traveller's guide",
  help: 'Help',
  incident: 'Happening',
}

export type EntryRef = {
  kind: EntryKind
  id?: string
}

export type EntrySearch = {
  entry?: string
  at?: string
}

function isEntryKind(value: string): value is EntryKind {
  return (ENTRY_KINDS as readonly string[]).includes(value)
}

function parseEntry(token: string): EntryRef | null {
  const [kind, ...rest] = token.split(ENTRY_ID_SEPARATOR)
  if (!isEntryKind(kind)) return null
  const id = rest.join(ENTRY_ID_SEPARATOR)
  if (SINGLETON_ENTRY_KINDS.has(kind)) return id ? null : { kind }
  return id ? { kind, id } : null
}

export function parseEntryStack(raw: unknown): EntryRef[] {
  if (typeof raw !== 'string' || raw.length === 0) return []
  return raw
    .split(ENTRY_SEPARATOR)
    .map(parseEntry)
    .filter((entry): entry is EntryRef => entry !== null)
    .slice(-MAX_ENTRY_DEPTH)
}

export function serializeEntry(entry: EntryRef): string {
  return entry.id === undefined
    ? entry.kind
    : `${entry.kind}${ENTRY_ID_SEPARATOR}${entry.id}`
}

export function serializeEntryStack(entries: EntryRef[]): string | undefined {
  if (entries.length === 0) return undefined
  return entries.map(serializeEntry).join(ENTRY_SEPARATOR)
}

export function sameEntry(left: EntryRef, right: EntryRef): boolean {
  return left.kind === right.kind && left.id === right.id
}

export function pushEntry(entries: EntryRef[], entry: EntryRef): EntryRef[] {
  const top = entries.at(-1)
  if (top && sameEntry(top, entry)) return entries
  return [...entries, entry].slice(-MAX_ENTRY_DEPTH)
}

const SECTION_ANCHOR = /^section-[a-z0-9_-]+$/

export function validateEntrySearch(
  search: Record<string, unknown>
): EntrySearch {
  const entry = serializeEntryStack(parseEntryStack(search.entry))
  if (entry === undefined) return {}
  const at =
    typeof search.at === 'string' && SECTION_ANCHOR.test(search.at)
      ? search.at
      : undefined
  return at === undefined ? { entry } : { entry, at }
}

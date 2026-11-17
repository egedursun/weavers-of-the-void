import {
  DRAWER_ENTRY_SEPARATOR,
  DRAWER_ID_SEPARATOR,
  MAX_DRAWER_DEPTH,
} from '@/constants/ui'

export const DRAWER_KINDS = [
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

export type DrawerKind = (typeof DRAWER_KINDS)[number]

export const SINGLETON_DRAWER_KINDS: ReadonlySet<DrawerKind> = new Set([
  'creator',
  'help',
])

export const DRAWER_KIND_LABEL: Record<DrawerKind, string> = {
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

export type DrawerEntry = {
  kind: DrawerKind
  id?: string
}

export type DrawerSearch = {
  drawer?: string
}

function isDrawerKind(value: string): value is DrawerKind {
  return (DRAWER_KINDS as readonly string[]).includes(value)
}

function parseEntry(token: string): DrawerEntry | null {
  const [kind, ...rest] = token.split(DRAWER_ID_SEPARATOR)
  if (!isDrawerKind(kind)) return null
  const id = rest.join(DRAWER_ID_SEPARATOR)
  if (SINGLETON_DRAWER_KINDS.has(kind)) return id ? null : { kind }
  return id ? { kind, id } : null
}

export function parseDrawerStack(raw: unknown): DrawerEntry[] {
  if (typeof raw !== 'string' || raw.length === 0) return []
  return raw
    .split(DRAWER_ENTRY_SEPARATOR)
    .map(parseEntry)
    .filter((entry): entry is DrawerEntry => entry !== null)
    .slice(-MAX_DRAWER_DEPTH)
}

export function serializeEntry(entry: DrawerEntry): string {
  return entry.id === undefined
    ? entry.kind
    : `${entry.kind}${DRAWER_ID_SEPARATOR}${entry.id}`
}

export function serializeDrawerStack(
  entries: DrawerEntry[]
): string | undefined {
  if (entries.length === 0) return undefined
  return entries.map(serializeEntry).join(DRAWER_ENTRY_SEPARATOR)
}

export function sameEntry(left: DrawerEntry, right: DrawerEntry): boolean {
  return left.kind === right.kind && left.id === right.id
}

export function pushDrawerEntry(
  entries: DrawerEntry[],
  entry: DrawerEntry
): DrawerEntry[] {
  const top = entries.at(-1)
  if (top && sameEntry(top, entry)) return entries
  return [...entries, entry].slice(-MAX_DRAWER_DEPTH)
}

export function validateDrawerSearch(
  search: Record<string, unknown>
): DrawerSearch {
  const drawer = serializeDrawerStack(parseDrawerStack(search.drawer))
  return drawer === undefined ? {} : { drawer }
}

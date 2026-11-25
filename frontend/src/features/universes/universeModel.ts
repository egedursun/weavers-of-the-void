import { formatDateTime, formatSince, formatInteger } from '@/lib/format'
import { plural } from '@/lib/units'
import { type UniverseFilters, type UniverseSummary } from './types'

export const NAME_MAX = 120
export const NOTES_MAX = 4000
export const TAG_MAX = 40
export const TAGS_MAX = 24
const RECENT_SHOWN = 4

export type UniverseAct =
  'notes' | 'cover' | 'duplicate' | 'export' | 'move' | 'delete' | 'details'

const RUNNING_REASON: Record<string, string> = {
  epoch: 'An epoch is running in this universe. Wait for it to end first.',
  export:
    'This universe is being exported. Wait for the file to be packed first.',
  import:
    'This universe is still being imported. Wait for it to be placed first.',
}

export function busyReason(
  universe: Pick<UniverseSummary, 'running_jobs'>
): string | null {
  const running = universe.running_jobs
  if (running.length === 0) return null
  const known = running.find((kind) => kind in RUNNING_REASON)
  return known === undefined
    ? 'Work is running in this universe. Wait for it to finish first.'
    : RUNNING_REASON[known]
}

export function archivedReason(universe: UniverseSummary): string | null {
  return universe.status === 'archived'
    ? 'This universe is archived. Restore it to the shelf first.'
    : null
}

export function ageLine(universe: UniverseSummary): string {
  return universe.opened_at
    ? `Last opened ${formatDateTime(universe.opened_at)}`
    : 'Never opened'
}

export function openedSince(universe: UniverseSummary): string {
  return universe.opened_at ? formatSince(universe.opened_at) : 'Never opened'
}

export function born(universe: Pick<UniverseSummary, 'epoch'>): boolean {
  return universe.epoch > 0
}

export function timeLine(
  universe: Pick<UniverseSummary, 'epoch' | 'year'>
): string {
  if (!born(universe)) return 'Not yet born'
  return `Epoch ${formatInteger(universe.epoch)} · Year ${formatInteger(universe.year)}`
}

export function cleanTags(raw: string): string[] {
  const seen = new Set<string>()
  for (const part of raw.split(',')) {
    const tag = part.trim().slice(0, TAG_MAX)
    if (tag) seen.add(tag)
  }
  return [...seen].slice(0, TAGS_MAX)
}

export function nameProblem(name: string): string | null {
  const trimmed = name.trim()
  if (!trimmed) return 'Give the universe a name.'
  if (trimmed.length > NAME_MAX)
    return `A name holds at most ${plural(NAME_MAX, 'character')}.`
  return null
}

export function narrowedCount(filters: UniverseFilters): number {
  return [
    filters.status !== 'active',
    filters.origin !== null,
    filters.tag !== null,
  ].filter(Boolean).length
}

export function frontRow(shelf: UniverseSummary[]): UniverseSummary[] {
  const pinned = shelf.filter((item) => item.pinned)
  const recent = shelf
    .filter((item) => !item.pinned && item.opened_at !== null)
    .slice(0, RECENT_SHOWN)
  return [...pinned, ...recent]
}

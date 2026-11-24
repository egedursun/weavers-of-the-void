import { type EntrySearch } from '@/components/layout/entry/entryStack'

export type MapSearch = EntrySearch & {
  world?: number
  epoch?: number
  focus?: number
  species?: number
}

function positive(value: unknown): number | undefined {
  const number = typeof value === 'string' ? Number(value) : value
  return typeof number === 'number' && Number.isInteger(number) && number > 0
    ? number
    : undefined
}

export function validateMapSearch(search: Record<string, unknown>): MapSearch {
  const result: MapSearch = {}
  const world = positive(search.world)
  const epoch = positive(search.epoch)
  const focus = positive(search.focus)
  const species = positive(search.species)
  if (world !== undefined) result.world = world
  if (epoch !== undefined) result.epoch = epoch
  if (focus !== undefined) result.focus = focus
  if (species !== undefined) result.species = species
  return result
}

export const COSMOS_PANELS = [
  'world',
  'voyages',
  'gods',
  'command',
  'star',
] as const

export type CosmosPanel = (typeof COSMOS_PANELS)[number]

export const COMMAND_SECTIONS = [
  'world',
  'star',
  'route',
  'sky',
  'quest',
  'climate',
  'federation',
  'resource',
  'economy',
  'mechanics',
  'orders',
  'beyond',
] as const

export type CommandSection = (typeof COMMAND_SECTIONS)[number]

export type CosmosSearch = {
  galaxy?: number
  world?: number
  star?: number
  panel?: CosmosPanel
  section?: CommandSection
}

function positiveInteger(value: unknown): number | undefined {
  const number = typeof value === 'string' ? Number(value) : value
  return typeof number === 'number' && Number.isInteger(number) && number > 0
    ? number
    : undefined
}

function oneOf<T extends string>(
  options: readonly T[],
  value: unknown
): T | undefined {
  return typeof value === 'string' &&
    (options as readonly string[]).includes(value)
    ? (value as T)
    : undefined
}

export function validateCosmosSearch(
  search: Record<string, unknown>
): CosmosSearch {
  const result: CosmosSearch = {}
  const galaxy = positiveInteger(search.galaxy)
  const world = positiveInteger(search.world)
  const star = positiveInteger(search.star)
  const panel = oneOf(COSMOS_PANELS, search.panel)
  const section = oneOf(COMMAND_SECTIONS, search.section)
  if (galaxy !== undefined) result.galaxy = galaxy
  if (world !== undefined) result.world = world
  if (star !== undefined) result.star = star
  if (panel !== undefined) result.panel = panel
  if (section !== undefined) result.section = section
  return result
}

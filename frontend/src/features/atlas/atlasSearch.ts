import { type DrawerSearch } from '@/components/layout/drawer/drawerEntries'

export const ATLAS_SORTS = [
  'name',
  'type',
  'epoch',
  'power',
  'importance',
] as const
export type AtlasSort = (typeof ATLAS_SORTS)[number]
export const ATLAS_VIEWS = ['tree', 'list'] as const
export type AtlasView = (typeof ATLAS_VIEWS)[number]
export const ATLAS_STATUSES = [
  'visible',
  'canon',
  'dead',
  'destroyed',
  'fulfilled',
  'rejected',
] as const
export type AtlasStatus = (typeof ATLAS_STATUSES)[number]

export type AtlasSearch = DrawerSearch & {
  q?: string
  type?: string
  world?: number
  status?: AtlasStatus
  sort?: AtlasSort
  desc?: boolean
  favorites?: boolean
  history?: boolean
  view?: AtlasView
  select?: string
  page?: number
}

function oneOf<T extends string>(
  value: unknown,
  options: readonly T[]
): T | undefined {
  return typeof value === 'string' &&
    (options as readonly string[]).includes(value)
    ? (value as T)
    : undefined
}

function flag(value: unknown): boolean | undefined {
  if (value === true || value === 'true' || value === 1 || value === '1')
    return true
  return undefined
}

function text(value: unknown): string | undefined {
  return typeof value === 'string' && value.trim() ? value : undefined
}

function positive(value: unknown): number | undefined {
  const number = typeof value === 'string' ? Number(value) : value
  return typeof number === 'number' && Number.isInteger(number) && number > 0
    ? number
    : undefined
}

export function validateAtlasSearch(
  search: Record<string, unknown>
): AtlasSearch {
  const result: AtlasSearch = {}
  if (typeof search.drawer === 'string') result.drawer = search.drawer
  const q = text(search.q)
  if (q) result.q = q
  const type = text(search.type)
  if (type) result.type = type
  const status = oneOf(search.status, ATLAS_STATUSES)
  if (status) result.status = status
  const sort = oneOf(search.sort, ATLAS_SORTS)
  if (sort) result.sort = sort
  if (flag(search.desc)) result.desc = true
  if (flag(search.favorites)) result.favorites = true
  if (flag(search.history)) result.history = true
  const view = oneOf(search.view, ATLAS_VIEWS)
  if (view) result.view = view
  const select = text(search.select)
  if (
    select &&
    /^(entity|son|creator|world|star|foreign-god):?\d*$/.test(select)
  )
    result.select = select
  const page = positive(search.page)
  if (page) result.page = page
  const world = positive(search.world)
  if (world) result.world = world
  return result
}

export function parseSelection(
  selection: string | null
): { kind: string; id: number | null } | null {
  if (!selection) return null
  const [kind, raw] = selection.split(':')
  const id = raw ? Number(raw) : null
  return { kind, id: id !== null && Number.isInteger(id) && id > 0 ? id : null }
}

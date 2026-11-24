import { type LucideIcon } from 'lucide-react'
import { ENTITY_TYPE_ICON } from '@/components/domain/domainIcons'
import { ENTRY_KIND_ICON } from '@/components/domain/entryKindIcon'
import { humanize } from '@/features/entity/actions/schema'
import { type ImageListView } from '@/features/images/api'

export const EVERY = '__every__'

export const SORTS = ['newest', 'oldest', 'important', 'name'] as const
export type GallerySort = (typeof SORTS)[number]

export const SORT_LABEL: Record<GallerySort, string> = {
  newest: 'Newest first',
  oldest: 'Oldest first',
  important: 'Most important',
  name: 'By name',
}

export const DIVINE_KINDS = new Set(['creator', 'son', 'foreign_god', 'world'])

const KIND_ICON: Record<string, LucideIcon> = {
  creator: ENTRY_KIND_ICON.creator,
  son: ENTRY_KIND_ICON.son,
  foreign_god: ENTRY_KIND_ICON['foreign-god'],
  world: ENTRY_KIND_ICON.world,
  star: ENTRY_KIND_ICON.star,
  entity: ENTRY_KIND_ICON.entity,
  galaxy: ENTRY_KIND_ICON.galaxy,
  cluster: ENTRY_KIND_ICON.cluster,
  dimension: ENTRY_KIND_ICON.dimension,
}

const KIND_LABEL: Record<string, string> = {
  creator: 'The Creator',
  son: 'Children',
  foreign_god: 'Foreign gods',
  world: 'Worlds',
  star: 'Stars',
  entity: 'Records',
  galaxy: 'Galaxies',
  cluster: 'Clusters',
  dimension: 'Dimensions',
}

export function categoryOf(item: ImageListView): string {
  if (item.target_type) return item.target_type
  return item.target_kind ?? 'entity'
}

export const CATEGORY_ICON: Record<string, LucideIcon | undefined> = {
  ...ENTITY_TYPE_ICON,
  ...KIND_ICON,
}

export const FALLBACK_ICON: LucideIcon = ENTRY_KIND_ICON.entity

export function categoryLabel(category: string): string {
  return KIND_LABEL[category] ?? humanize(category)
}

export function divineRank(item: ImageListView): number {
  const order = ['creator', 'son', 'foreign_god', 'world']
  const index = order.indexOf(item.target_kind ?? '')
  return index === -1 ? order.length : index
}

export function sortImages(
  items: ImageListView[],
  sort: GallerySort
): ImageListView[] {
  const sorted = [...items]
  if (sort === 'newest')
    sorted.sort((left, right) =>
      right.image.created_at.localeCompare(left.image.created_at)
    )
  if (sort === 'oldest')
    sorted.sort((left, right) =>
      left.image.created_at.localeCompare(right.image.created_at)
    )
  if (sort === 'important')
    sorted.sort(
      (left, right) =>
        divineRank(left) - divineRank(right) ||
        (right.target_importance ?? 0) - (left.target_importance ?? 0)
    )
  if (sort === 'name')
    sorted.sort((left, right) =>
      (left.target_name ?? '').localeCompare(right.target_name ?? '')
    )
  return sorted
}

export function countBy<T>(
  items: T[],
  key: (item: T) => string
): [string, number][] {
  const map = new Map<string, number>()
  for (const item of items) map.set(key(item), (map.get(key(item)) ?? 0) + 1)
  return [...map.entries()].sort((left, right) => right[1] - left[1])
}

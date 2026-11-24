import type { components } from '@/api/generated/schema'
import { type EntryKind } from '@/components/layout/entry/entryStack'

type NodeKind = components['schemas']['NodeKind']

const DRAWER_OF: Record<NodeKind, EntryKind> = {
  creator: 'creator',
  son: 'son',
  foreign_god: 'foreign-god',
  world: 'world',
  star: 'star',
  galaxy: 'galaxy',
  cluster: 'cluster',
  dimension: 'dimension',
  entity: 'entity',
}

export function entryKindOf(kind: NodeKind | undefined): EntryKind {
  return kind ? DRAWER_OF[kind] : 'son'
}

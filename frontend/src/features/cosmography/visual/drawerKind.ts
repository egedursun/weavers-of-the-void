import type { components } from '@/api/generated/schema'
import { type DrawerKind } from '@/components/layout/drawer/drawerEntries'

type NodeKind = components['schemas']['NodeKind']

const DRAWER_OF: Record<NodeKind, DrawerKind> = {
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

export function drawerKindOf(kind: NodeKind | undefined): DrawerKind {
  return kind ? DRAWER_OF[kind] : 'son'
}

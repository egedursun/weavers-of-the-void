import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'
import { type DrawerKind } from '@/components/layout/drawer/drawerEntries'

export type NameEntry = components['schemas']['NameEntry']
export type NodeKind = components['schemas']['NodeKind']
export type NodeIndex = Map<number, NameEntry>

export const nodeKeys = {
  names: [...queryKeys.world.all, 'names'] as const,
}

export const DRAWER_OF_NODE: Record<NodeKind, DrawerKind | null> = {
  entity: 'entity',
  son: 'son',
  foreign_god: 'foreign-god',
  creator: 'creator',
  world: 'world',
  star: 'star',
}

export function useNodeIndex(): NodeIndex {
  const names = useQuery({
    queryKey: nodeKeys.names,
    queryFn: () => unwrap(api.GET('/api/names')),
  })
  return useMemo(
    () => new Map((names.data ?? []).map((entry) => [entry.id, entry])),
    [names.data]
  )
}

import { useMemo } from 'react'
import { type LinkTarget } from '@/components/domain/nameLinks'
import { type DrawerKind } from '@/components/layout/drawer/drawerEntries'
import { useNames } from '@/features/entity/api/queries'
import { type NameEntry, type NodeRef } from '@/features/entity/api/types'

const DRAWER_OF_NODE: Partial<Record<string, DrawerKind>> = {
  entity: 'entity',
  son: 'son',
  foreign_god: 'foreign-god',
  creator: 'creator',
  world: 'world',
  star: 'star',
}

export function drawerKindOf(kind: string): DrawerKind | undefined {
  return DRAWER_OF_NODE[kind]
}

export function targetOf(
  entry: Pick<NameEntry, 'id' | 'name' | 'kind'>
): LinkTarget | null {
  const kind = drawerKindOf(entry.kind)
  return kind ? { id: entry.id, name: entry.name, kind } : null
}

export function targetsOfRefs(
  refs: (NodeRef | null | undefined)[]
): LinkTarget[] {
  return refs
    .map((ref) => (ref ? targetOf(ref) : null))
    .filter((target): target is LinkTarget => target !== null)
}

export function useNameIndex() {
  const names = useNames()
  return useMemo(() => {
    const map = new Map<number, NameEntry>()
    for (const entry of names.data ?? []) map.set(entry.id, entry)
    return map
  }, [names.data])
}

export function useLinkTargets(ids: number[]): LinkTarget[] {
  const index = useNameIndex()
  const key = ids.join(',')
  return useMemo(
    () =>
      key
        .split(',')
        .filter(Boolean)
        .map((id) => index.get(Number(id)))
        .map((entry) => (entry ? targetOf(entry) : null))
        .filter((target): target is LinkTarget => target !== null),
    [index, key]
  )
}

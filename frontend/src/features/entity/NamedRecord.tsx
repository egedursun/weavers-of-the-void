import { useMemo } from 'react'
import { EntityLink } from '@/components/domain'
import { type DrawerKind } from '@/components/layout/drawer/drawerEntries'
import { Muted } from '@/components/typography'
import { useNames } from './api/queries'
import { type NodeKind } from './api/types'

const DRAWER_OF: Record<NodeKind, DrawerKind> = {
  entity: 'entity',
  son: 'son',
  creator: 'creator',
  foreign_god: 'foreign-god',
  world: 'world',
  star: 'star',
  galaxy: 'galaxy',
  cluster: 'cluster',
  dimension: 'dimension',
}

export function NamedRecord({
  id,
  fallback = 'Unknown',
}: {
  id: number | null | undefined
  fallback?: string
}) {
  const names = useNames()
  const entry = useMemo(
    () =>
      id === null || id === undefined
        ? undefined
        : names.data?.find((item) => item.id === id),
    [names.data, id]
  )
  if (!entry) return <Muted as='span'>{fallback}</Muted>
  return (
    <EntityLink kind={DRAWER_OF[entry.kind]} id={String(entry.id)} showIcon>
      {entry.name}
    </EntityLink>
  )
}

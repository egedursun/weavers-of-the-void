import { type ReactNode } from 'react'
import { EntityLink } from '@/components/domain'
import { DRAWER_OF_NODE, type NodeIndex } from './nodes'

type NodeLinkProps = {
  nodeId: number
  index: NodeIndex
  fallback?: ReactNode
}

export function NodeLink({ nodeId, index, fallback }: NodeLinkProps) {
  const entry = index.get(nodeId)
  const drawer = entry ? DRAWER_OF_NODE[entry.kind] : null
  if (!entry || !drawer) return <>{fallback ?? `#${nodeId}`}</>
  if (drawer === 'creator' || drawer === 'help')
    return (
      <EntityLink kind='creator' showIcon>
        {entry.name}
      </EntityLink>
    )
  return (
    <EntityLink kind={drawer} id={String(entry.id)} showIcon>
      {entry.name}
    </EntityLink>
  )
}

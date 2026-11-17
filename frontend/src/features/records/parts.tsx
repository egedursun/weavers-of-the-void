import { type ReactNode } from 'react'
import { EntityLink } from '@/components/domain'
import { Muted } from '@/components/typography'
import { DRAWER_OF_NODE, useNodeIndex } from '@/features/feed/nodes'
import { type EventChange, type EventFact } from './api'
import { amountText, spokenKey } from './format'

export function NodeRef({
  id,
  name,
}: {
  id: number | null
  name: string | null
}) {
  const index = useNodeIndex()
  if (id === null) return <Muted as='span'>{name ?? 'No one'}</Muted>
  const entry = index.get(id)
  const kind = entry ? DRAWER_OF_NODE[entry.kind] : 'entity'
  const shown = name ?? entry?.name ?? 'A record no longer named'
  if (kind === null) return <Muted as='span'>{shown}</Muted>
  return (
    <EntityLink kind={kind} id={String(id)} showIcon>
      {shown}
    </EntityLink>
  )
}

export function FactValueText({ fact }: { fact: EventFact }): ReactNode {
  if (fact.node_id !== null)
    return <NodeRef id={fact.node_id} name={fact.node_name} />
  if (fact.number !== null) return amountText(fact.number, fact.unit)
  if (fact.enum_value !== null) return spokenKey(fact.enum_value)
  return fact.name ?? 'Not known'
}

export function ChangeSide({
  change,
  side,
}: {
  change: EventChange
  side: 'before' | 'after'
}) {
  const number = side === 'before' ? change.before_number : change.after_number
  const text = side === 'before' ? change.before_text : change.after_text
  const nodeId =
    side === 'before' ? change.before_node_id : change.after_node_id
  const nodeName =
    side === 'before' ? change.before_node_name : change.after_node_name
  if (nodeId !== null) return <NodeRef id={nodeId} name={nodeName} />
  if (number !== null) return <span>{amountText(number, null)}</span>
  if (text === null) return <Muted as='span'>Nothing</Muted>
  return <span>{text.length > 80 ? `${text.slice(0, 80)}…` : text}</span>
}

import { useId, useState } from 'react'
import { Input } from '@/components/ui/input'
import { findNode } from './graphModel'

export type PickableNode = { id: number; name: string }

type NodePickerProps = {
  nodes: readonly PickableNode[]
  value: number | null
  onPick: (id: number | null) => void
  label: string
  placeholder: string
  listId?: string
}

export function NodeOptions({
  id,
  nodes,
}: {
  id: string
  nodes: readonly PickableNode[]
}) {
  return (
    <datalist id={id}>
      {nodes.map((node) => (
        <option key={node.id} value={node.name} />
      ))}
    </datalist>
  )
}

export function NodePicker({
  nodes,
  value,
  onPick,
  label,
  placeholder,
  listId,
}: NodePickerProps) {
  const ownList = useId()
  const list = listId ?? ownList
  const chosen = nodes.find((node) => node.id === value)
  const [draft, setDraft] = useState<string | null>(null)
  const text = draft ?? chosen?.name ?? ''
  return (
    <>
      <Input
        size='sm'
        type='search'
        list={list}
        value={text}
        aria-label={label}
        placeholder={placeholder}
        className='w-full'
        onChange={(event) => {
          const next = event.target.value
          const match = findNode(nodes, next)
          if (match) {
            setDraft(null)
            onPick(match.id)
          } else {
            setDraft(next)
            if (!next) onPick(null)
          }
        }}
      />
      {!listId && <NodeOptions id={list} nodes={nodes} />}
    </>
  )
}

import { useId, useState } from 'react'
import { type LucideIcon, Plus, X } from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { FieldTile, PagedList } from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import { Chip } from '@/features/cosmography/parts'
import { NodePicker } from '@/features/dominion/parts'
import { useNames } from '@/features/entity/api/queries'

type NodeRef = components['schemas']['NodeRef']

export function StepButton({
  icon: Icon,
  label,
  busy,
  onClick,
  variant = 'outline',
}: {
  icon: LucideIcon
  label: string
  busy: string | null
  onClick: () => void
  variant?: 'outline' | 'default' | 'ghost'
}) {
  return (
    <Button
      size='sm'
      variant={variant}
      disabled={busy !== null}
      disabledReason={busy ?? undefined}
      onClick={onClick}
    >
      <Icon />
      {label}
    </Button>
  )
}

export function NodeChips({
  nodes,
  empty,
  icon,
}: {
  nodes: NodeRef[]
  empty: string
  icon?: LucideIcon
}) {
  if (nodes.length === 0) return <Muted variant='caption'>{empty}</Muted>
  return (
    <PagedList
      items={nodes}
      initial={8}
      noun={['stop', 'stops']}
      className='flex min-w-0 flex-wrap gap-2'
      itemKey={(node, index) => `${node.id}-${index}`}
    >
      {(node, index) => <Chip icon={icon}>{`${index + 1}. ${node.name}`}</Chip>}
    </PagedList>
  )
}

export function NodeListPicker({
  label,
  value,
  types,
  kinds,
  blocked,
  onChange,
}: {
  label: string
  value: number[]
  types?: readonly string[]
  kinds?: readonly string[]
  blocked: string | null
  onChange: (value: number[]) => void
}) {
  const names = useNames()
  const [next, setNext] = useState<number | null>(null)
  const named = (id: number) =>
    names.data?.find((entry) => entry.id === id)?.name ?? `#${id}`
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <Label variant='overline'>{`${label} (${value.length})`}</Label>
      <div className='flex min-w-0 flex-wrap gap-2'>
        {value.length === 0 ? (
          <Muted variant='caption'>None chosen yet</Muted>
        ) : (
          value.map((id, index) => (
            <Button
              key={`${id}-${index}`}
              size='sm'
              variant='secondary'
              aria-label={`Take out ${named(id)}`}
              disabled={blocked !== null}
              disabledReason={blocked ?? undefined}
              onClick={() => onChange(value.filter((_, at) => at !== index))}
            >
              {`${index + 1}. ${named(id)}`}
              <X />
            </Button>
          ))
        )}
      </div>
      <div className='flex min-w-0 items-end gap-2'>
        <div className='min-w-0 flex-1'>
          <NodePicker
            label={`Add to ${label.toLowerCase()}`}
            value={next}
            onChange={setNext}
            blocked={blocked}
            types={types}
            kinds={kinds}
          />
        </div>
        <Button
          size='sm'
          variant='outline'
          disabled={blocked !== null || next === null}
          disabledReason={blocked ?? 'Choose one to add first'}
          onClick={() => {
            if (next !== null) onChange([...value, next])
            setNext(null)
          }}
        >
          <Plus />
          Add
        </Button>
      </div>
    </div>
  )
}

export function TextField({
  label,
  value,
  blocked,
  onChange,
}: {
  label: string
  value: string
  blocked: string | null
  onChange: (value: string) => void
}) {
  const id = useId()
  return (
    <FieldTile id={id} label={label}>
      <Input
        id={id}
        value={value}
        disabled={blocked !== null}
        onChange={(event) => onChange(event.target.value)}
      />
    </FieldTile>
  )
}

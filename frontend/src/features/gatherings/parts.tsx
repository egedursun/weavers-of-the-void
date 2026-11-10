import { useId, useMemo } from 'react'
import { RecordCombobox } from '@/components/domain/RecordCombobox'
import { Label, Muted } from '@/components/typography'
import { useNames } from '@/features/entity/api/queries'
import { RefLink } from '@/features/entity/realm/parts'

const GOD_KINDS = new Set(['son', 'creator', 'foreign_god', 'world', 'star'])

export type NodeRef = { id: number; kind: string; name: string }

export function Ref({
  node,
  empty = 'no one',
}: {
  node: NodeRef | null | undefined
  empty?: string
}) {
  if (!node) return <Muted as='span'>{empty}</Muted>
  return <RefLink node={node} />
}

export function ThingPicker({
  label,
  value,
  onChange,
  blocked,
  types,
}: {
  label: string
  value: number | null
  onChange: (value: number | null) => void
  blocked: string | null
  types?: readonly string[]
}) {
  const id = useId()
  const names = useNames()
  const options = useMemo(
    () =>
      (names.data ?? [])
        .filter((entry) =>
          entry.kind === 'entity'
            ? entry.status !== 'dead' &&
              (types === undefined || types.includes(entry.type))
            : types === undefined && GOD_KINDS.has(entry.kind)
        )
        .map((entry) => ({
          value: String(entry.id),
          label: entry.name,
          hint: (entry.kind === 'entity' ? entry.type : entry.kind).replaceAll(
            '_',
            ' '
          ),
        })),
    [names.data, types]
  )
  return (
    <div className='flex min-w-0 flex-col gap-1'>
      <Label as='label' htmlFor={id}>
        {label}
      </Label>
      <RecordCombobox
        id={id}
        options={options}
        value={value === null ? null : String(value)}
        onChange={(next) => onChange(next === null ? null : Number(next))}
        placeholder={
          types === undefined
            ? 'Search any being, god or world'
            : `Search ${types.map((type) => type.replaceAll('_', ' ')).join(' or ')}`
        }
        disabled={blocked !== null}
        disabledReason={blocked ?? undefined}
        clearable
        aria-label={label}
      />
    </div>
  )
}

import { useId, useMemo } from 'react'
import { Lock, LockOpen, type LucideIcon, Save, Trash2 } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label as FieldLabel } from '@/components/ui/label'
import { RecordCombobox } from '@/components/domain/RecordCombobox'
import { useNames } from '@/features/entity/api/queries'
import { busyOf } from './labels'
import { type Values, type useRecordActions } from './recordHooks'

const PLURAL: Record<string, string> = {
  region: 'regions',
  mortal: 'mortals',
  army: 'armies',
  settlement: 'settlements',
  house: 'houses',
  place: 'places',
  resource: 'resources',
}

function searchHint(types: string[]): string {
  const known = [...new Set(types.map((type) => PLURAL[type] ?? 'communities'))]
  return `Search ${known.slice(0, 2).join(' or ')}${known.length > 2 ? ' and more' : ''}…`
}

export function EntityPicker({
  label,
  types,
  value,
  onChange,
  blocked,
  icon: Icon,
}: {
  label: string
  types: string[]
  value: number | null
  onChange: (value: number | null) => void
  blocked: string | null
  icon?: LucideIcon
}) {
  const id = useId()
  const names = useNames()
  const options = useMemo(
    () =>
      (names.data ?? [])
        .filter(
          (entry) =>
            entry.kind === 'entity' &&
            types.includes(entry.type) &&
            entry.status !== 'dead'
        )
        .map((entry) => ({
          value: String(entry.id),
          label: entry.name,
          hint: entry.type.replaceAll('_', ' '),
        })),
    [names.data, types]
  )
  return (
    <div className='flex min-w-0 flex-col gap-1.5 rounded-md border surface-framed border-gild/70 bg-card p-2.5'>
      <div className='flex min-w-0 items-center gap-1.5'>
        {Icon && (
          <Icon
            aria-hidden='true'
            className='size-icon-xs shrink-0 text-muted-foreground'
          />
        )}
        <FieldLabel htmlFor={id} className='min-w-0 flex-1 truncate'>
          {label}
        </FieldLabel>
      </div>
      <RecordCombobox
        id={id}
        options={options}
        value={value === null ? null : String(value)}
        onChange={(next) => onChange(next === null ? null : Number(next))}
        placeholder={searchHint(types)}
        disabled={blocked !== null}
        disabledReason={blocked ?? undefined}
        clearable
        aria-label={label}
      />
    </div>
  )
}

export function RecordButtons({
  actions,
  values,
  locked,
  blocked,
  deletable = true,
  removeLabel = 'Strike out',
}: {
  actions: ReturnType<typeof useRecordActions>
  values: Values
  locked: string[]
  blocked: string | null
  deletable?: boolean
  removeLabel?: string
}) {
  const busy = busyOf(
    blocked,
    actions.save.isPending,
    actions.release.isPending,
    actions.remove.isPending
  )
  const empty = Object.keys(values).length === 0
  const why = (off: boolean, reason: string) =>
    off ? (busy ?? reason) : undefined
  return (
    <div className='flex flex-wrap gap-2'>
      <Button
        size='sm'
        disabled={busy !== null || empty}
        disabledReason={why(busy !== null || empty, 'Change a value first')}
        onClick={() => actions.save.mutate({ values, hold: true })}
      >
        <Lock />
        Set and hold
      </Button>
      <Button
        size='sm'
        variant='outline'
        disabled={busy !== null || empty}
        disabledReason={why(busy !== null || empty, 'Change a value first')}
        onClick={() => actions.save.mutate({ values, hold: false })}
      >
        <Save />
        Set once
      </Button>
      <Button
        size='sm'
        variant='outline'
        disabled={busy !== null || locked.length === 0}
        disabledReason={why(
          busy !== null || locked.length === 0,
          'Nothing is held'
        )}
        onClick={() => actions.release.mutate()}
      >
        <LockOpen />
        Release holds
      </Button>
      {deletable && (
        <Button
          size='sm'
          variant='destructive'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => actions.remove.mutate()}
        >
          <Trash2 />
          {removeLabel}
        </Button>
      )}
    </div>
  )
}

export function Held({ locked }: { locked: string[] }) {
  if (locked.length === 0) return null
  return (
    <Badge size='sm' variant='outline'>
      <Lock aria-hidden='true' />
      {locked.length} held
    </Badge>
  )
}

export function TextField({
  label,
  icon: Icon,
  value,
  onChange,
  placeholder,
}: {
  label: string
  icon?: LucideIcon
  value: string
  onChange: (value: string) => void
  placeholder?: string
}) {
  const id = useId()
  return (
    <div className='flex min-w-0 flex-col gap-1.5 rounded-md border surface-framed border-gild/70 bg-card p-2.5'>
      <div className='flex min-w-0 items-center gap-1.5'>
        {Icon && (
          <Icon
            aria-hidden='true'
            className='size-icon-xs shrink-0 text-muted-foreground'
          />
        )}
        <FieldLabel htmlFor={id} className='min-w-0 flex-1 truncate'>
          {label}
        </FieldLabel>
      </div>
      <Input
        id={id}
        value={value}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
      />
    </div>
  )
}

import { type ReactNode, useId, useMemo, useState } from 'react'
import { type LucideIcon, Save } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { type ProgressTone } from '@/components/ui/progress'
import { Textarea } from '@/components/ui/textarea'
import { EntityLink, Medallion, StatBar } from '@/components/domain'
import { type KpiTone } from '@/components/domain/KpiTile'
import { RecordCombobox } from '@/components/domain/RecordCombobox'
import { type DrawerKind } from '@/components/layout/drawer/drawerEntries'
import { Label, Muted, Text } from '@/components/typography'
import { EntityPicker } from '@/features/cosmos/EntityPicker'
import { useNames } from '@/features/entity/api/queries'
import { MindPicker } from '@/features/entity/mind/parts'
import { AdjustPanel, Held, NumberField } from '@/features/entity/wilds/parts'
import { heldLabel } from './labels'

export type Field =
  | {
      key: string
      label: string
      kind: 'number'
      min?: number
      max?: number
    }
  | { key: string; label: string; kind: 'decimal'; min?: number }
  | { key: string; label: string; kind: 'pick'; table: Record<string, string> }
  | { key: string; label: string; kind: 'text'; long?: boolean }
  | {
      key: string
      label: string
      kind: 'node'
      types: readonly string[]
      kinds?: readonly string[]
    }

export type Values = Record<string, number | string | boolean | null>

const WHOLE = /^\d+$/

function picked(text: string): number | string | boolean | null {
  if (text === 'none') return null
  if (text === 'true' || text === 'false') return text === 'true'
  return WHOLE.test(text) ? Number(text) : text
}

function parsed(field: Field, text: string): number | string | boolean | null {
  if (field.kind === 'text') return text.trim() === '' ? null : text.trim()
  if (text === '') return null
  if (field.kind === 'pick') return picked(text)
  if (field.kind === 'node') return Number(text)
  const value = Number(text)
  return Number.isNaN(value) ? null : value
}

function LinkField({
  label,
  value,
  types,
  kinds,
  busy,
  onChange,
}: {
  label: string
  value: string
  types: readonly string[]
  kinds: readonly string[]
  busy: string | null
  onChange: (value: string) => void
}) {
  const id = useId()
  const names = useNames()
  const options = useMemo(
    () =>
      (names.data ?? [])
        .filter((entry) =>
          entry.kind === 'entity'
            ? entry.status !== 'dead' && types.includes(entry.type)
            : kinds.includes(entry.kind)
        )
        .map((entry) => ({
          value: String(entry.id),
          label: entry.name,
          hint: (entry.kind === 'entity' ? entry.type : entry.kind).replaceAll(
            '_',
            ' '
          ),
        })),
    [names.data, types, kinds]
  )
  const sought = [...kinds, ...types]
    .map((kind) => kind.replaceAll('_', ' '))
    .join(', ')
  return (
    <div className='flex min-w-0 flex-col gap-1'>
      <Label as='label' htmlFor={id}>
        {label}
      </Label>
      <RecordCombobox
        id={id}
        options={options}
        value={value === '' ? null : value}
        onChange={(next) => onChange(next ?? '')}
        placeholder={`Search ${sought}`}
        disabled={busy !== null || names.isPending}
        disabledReason={
          busy ?? (names.isPending ? 'Reading the names' : undefined)
        }
        clearable
        aria-label={label}
      />
    </div>
  )
}

export function RecordEditor({
  title,
  note,
  fields,
  locked,
  busy,
  saveLabel = 'Hold these values',
  onSave,
  onRelease,
}: {
  title: string
  note: string
  fields: readonly Field[]
  locked: readonly string[]
  busy: string | null
  saveLabel?: string
  onSave: (values: Values) => void
  onRelease: (keys: string[]) => void
}) {
  const [draft, setDraft] = useState<Record<string, string>>({})
  const changed = Object.fromEntries(
    fields
      .filter((field) => (draft[field.key] ?? '') !== '')
      .map((field) => [field.key, parsed(field, draft[field.key] ?? '')])
  )
  const nothing =
    Object.keys(changed).length === 0 ? 'Change a value first' : null
  const set = (key: string) => (value: string) =>
    setDraft((previous) => ({ ...previous, [key]: value }))
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <Held
        keys={locked}
        label={(key) =>
          fields.find((field) => field.key === key)?.label ?? heldLabel(key)
        }
        busy={busy}
        onRelease={() => onRelease([...locked])}
      />
      <AdjustPanel title={title} note={note}>
        <div className='@container/fields min-w-0'>
          <div className='grid min-w-0 grid-cols-1 gap-2 @sm/fields:grid-cols-2'>
            {fields.map((field) =>
              field.kind === 'text' ? (
                <TextField
                  key={field.key}
                  label={field.label}
                  long={field.long ?? false}
                  value={draft[field.key] ?? ''}
                  disabled={busy !== null}
                  onChange={set(field.key)}
                />
              ) : field.kind === 'node' ? (
                <LinkField
                  key={field.key}
                  label={field.label}
                  value={draft[field.key] ?? ''}
                  types={field.types}
                  kinds={field.kinds ?? []}
                  busy={busy}
                  onChange={set(field.key)}
                />
              ) : field.kind === 'pick' ? (
                <MindPicker
                  key={field.key}
                  label={field.label}
                  value={draft[field.key] ?? ''}
                  table={field.table}
                  blocked={
                    busy ??
                    (Object.keys(field.table).length === 0
                      ? `No ${field.label.toLowerCase()} to choose from yet`
                      : null)
                  }
                  onPick={set(field.key)}
                />
              ) : (
                <NumberField
                  key={field.key}
                  label={field.label}
                  value={draft[field.key] ?? ''}
                  min={field.min}
                  max={field.kind === 'number' ? field.max : undefined}
                  disabled={busy !== null}
                  onChange={set(field.key)}
                />
              )
            )}
          </div>
        </div>
        <Button
          size='sm'
          disabled={busy !== null || nothing !== null}
          disabledReason={busy ?? nothing ?? undefined}
          onClick={() => {
            onSave(changed)
            setDraft({})
          }}
        >
          <Save />
          {saveLabel}
        </Button>
      </AdjustPanel>
    </div>
  )
}

function TextField({
  label,
  long,
  value,
  disabled,
  onChange,
}: {
  label: string
  long: boolean
  value: string
  disabled: boolean
  onChange: (value: string) => void
}) {
  const id = useId()
  return (
    <div
      className={cn(
        'flex min-w-0 flex-col gap-1',
        long && '@sm/fields:col-span-2'
      )}
    >
      <Label as='label' htmlFor={id}>
        {label}
      </Label>
      {long ? (
        <Textarea
          id={id}
          value={value}
          disabled={disabled}
          onChange={(event) => onChange(event.target.value)}
        />
      ) : (
        <Input
          id={id}
          value={value}
          disabled={disabled}
          onChange={(event) => onChange(event.target.value)}
        />
      )}
    </div>
  )
}

export function Meter({
  label,
  value,
  max = 100,
  tone = 'default',
  icon,
}: {
  label: string
  value: number
  max?: number
  tone?: ProgressTone
  icon?: LucideIcon
}) {
  return (
    <StatBar label={label} value={value} max={max} tone={tone} icon={icon} />
  )
}

export function RecordRow({
  icon,
  tone,
  title,
  caption,
  aside,
  children,
}: {
  icon: LucideIcon
  tone: KpiTone
  title: ReactNode
  caption?: ReactNode
  aside?: ReactNode
  children?: ReactNode
}) {
  return (
    <li className='flex min-w-0 flex-col gap-2 rounded-lg border bg-muted/30 p-3'>
      <div className='flex min-w-0 items-center gap-2'>
        <Medallion icon={icon} tone={tone} size='sm' />
        <div className='flex min-w-0 flex-1 flex-col gap-0.5'>
          <Text as='span' weight='semibold' truncate>
            {title}
          </Text>
          {caption && (
            <Muted as='span' variant='caption' truncate>
              {caption}
            </Muted>
          )}
        </div>
        {aside}
      </div>
      {children}
    </li>
  )
}

export function NodeLink({
  kind,
  id,
  name,
}: {
  kind: DrawerKind
  id: number | null | undefined
  name: string | null | undefined
}) {
  if (id === null || id === undefined)
    return <Muted as='span'>{name ?? 'None'}</Muted>
  return (
    <EntityLink kind={kind} id={String(id)} showIcon>
      {name ?? 'Unnamed'}
    </EntityLink>
  )
}

export function Facts({ items }: { items: [string, ReactNode][] }) {
  return (
    <div className='@container/facts w-full min-w-0'>
      <dl className='grid min-w-0 grid-cols-1 gap-x-4 gap-y-1.5 @md/facts:grid-cols-2'>
        {items.map(([label, value]) => (
          <div
            key={label}
            className='flex min-w-0 items-baseline justify-between gap-2 border-b border-dashed pb-1'
          >
            <dt className='shrink-0'>
              <Muted as='span' variant='caption'>
                {label}
              </Muted>
            </dt>
            <dd className='min-w-0 truncate text-right'>{value}</dd>
          </div>
        ))}
      </dl>
    </div>
  )
}

export function Chip({
  icon: Icon,
  children,
  variant = 'outline',
}: {
  icon?: LucideIcon
  children: ReactNode
  variant?:
    | 'outline'
    | 'default'
    | 'destructive'
    | 'info'
    | 'secondary'
    | 'success'
    | 'warning'
}) {
  return (
    <Badge size='sm' variant={variant}>
      {Icon && <Icon />}
      {children}
    </Badge>
  )
}

export function RecordPick({
  label,
  types,
  value,
  onChange,
  worldId,
}: {
  label: string
  types: readonly string[]
  value: number | null
  onChange: (id: number | null) => void
  worldId?: number
}) {
  return (
    <div className='flex min-w-0 flex-col gap-1'>
      <Label>{label}</Label>
      <EntityPicker
        types={types}
        value={value}
        onChange={onChange}
        placeholder={`Choose a ${label.toLowerCase()}`}
        worldId={worldId}
      />
    </div>
  )
}

const FORGE_COLUMNS = {
  2: '@lg/forge:grid-cols-2',
  3: '@lg/forge:grid-cols-3',
  4: '@lg/forge:grid-cols-2 @4xl/forge:grid-cols-4',
} as const

export function ForgeCard({
  icon,
  tone,
  title,
  note,
  columns,
  meta,
  action,
  children,
}: {
  icon: LucideIcon
  tone: KpiTone
  title: string
  note: string
  columns: keyof typeof FORGE_COLUMNS
  meta?: ReactNode
  action: ReactNode
  children: ReactNode
}) {
  return (
    <div
      data-surface='ForgeCard'
      className='@container/forge flex min-w-0 flex-col gap-3 rounded-xl border bg-card p-3 shadow-xs'
    >
      <div className='flex min-w-0 items-center gap-3'>
        <Medallion icon={icon} tone={tone} size='sm' />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Text weight='semibold'>{title}</Text>
          <Muted variant='caption'>{note}</Muted>
        </div>
      </div>
      <div
        className={cn(
          'grid min-w-0 grid-cols-1 items-end gap-3',
          FORGE_COLUMNS[columns]
        )}
      >
        {children}
      </div>
      <div className='flex min-w-0 flex-wrap items-center justify-between gap-2 border-t pt-3'>
        <div className='flex min-w-0 flex-wrap items-center gap-1'>{meta}</div>
        {action}
      </div>
    </div>
  )
}

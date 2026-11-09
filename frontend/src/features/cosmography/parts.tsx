import { type ReactNode, useState } from 'react'
import { type LucideIcon, Save } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { type ProgressTone } from '@/components/ui/progress'
import { EntityLink, Medallion, StatBar } from '@/components/domain'
import { type KpiTone } from '@/components/domain/KpiTile'
import { type DrawerKind } from '@/components/layout/drawer/drawerEntries'
import { Label, Muted, Text } from '@/components/typography'
import { EntityPicker } from '@/features/cosmos/EntityPicker'
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

export type Values = Record<string, number | string | null>

function parsed(field: Field, text: string): number | string | null {
  if (text === '') return null
  if (field.kind === 'pick') return text === 'none' ? null : text
  const value = Number(text)
  return Number.isNaN(value) ? null : value
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
        label={heldLabel}
        busy={busy}
        onRelease={() => onRelease([...locked])}
      />
      <AdjustPanel title={title} note={note}>
        <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
          {fields.map((field) =>
            field.kind === 'pick' ? (
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
      {name ?? `#${id}`}
    </EntityLink>
  )
}

export function Facts({ items }: { items: [string, ReactNode][] }) {
  return (
    <dl className='grid min-w-0 grid-cols-1 gap-x-4 gap-y-1.5 sm:grid-cols-2'>
      {items.map(([label, value]) => (
        <div
          key={label}
          className='flex min-w-0 items-baseline justify-between gap-2 border-b border-dashed pb-1'
        >
          <dt>
            <Muted as='span' variant='caption'>
              {label}
            </Muted>
          </dt>
          <dd className='min-w-0 truncate text-right'>{value}</dd>
        </div>
      ))}
    </dl>
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

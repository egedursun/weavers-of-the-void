import { type ReactNode, useId, useMemo, useState } from 'react'
import { ChevronDown, ChevronUp, type LucideIcon } from 'lucide-react'
import { type ActProp } from '@/api/mutation'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { FieldTile, Medallion } from '@/components/domain'
import { type KpiTone } from '@/components/domain/KpiTile'
import { RecordCombobox } from '@/components/domain/RecordCombobox'
import { Label, Muted, Text } from '@/components/typography'
import { useNames } from '@/features/entity/api/queries'

export function MindCard({
  title,
  icon,
  children,
  wide,
  hint,
}: {
  title: string
  icon: LucideIcon
  children: ReactNode
  wide?: boolean
  hint?: string
}) {
  return (
    <div
      className={
        wide
          ? '@container/mind flex min-w-0 flex-col gap-4 rounded-md border surface-framed border-gild/70 bg-card p-4 @xl/mind:col-span-2'
          : '@container/mind flex min-w-0 flex-col gap-4 rounded-md border surface-framed border-gild/70 bg-card p-4'
      }
    >
      <div className='flex min-w-0 items-center gap-2'>
        <Medallion icon={icon} size='sm' />
        <div className='flex min-w-0 flex-col'>
          <Label variant='overline'>{title}</Label>
          {hint && <Muted variant='caption'>{hint}</Muted>}
        </div>
      </div>
      {children}
    </div>
  )
}

export function MindPicker({
  label,
  value,
  table,
  blocked,
  placeholder,
  onPick,
  act,
}: {
  label: string
  value: string
  table: Record<string, string>
  blocked: string | null
  placeholder?: string
  onPick: (value: string) => void
  act?: ActProp
}) {
  const id = useId()
  return (
    <FieldTile id={id} label={label}>
      <Select
        act={act}
        value={value}
        onValueChange={onPick}
        disabled={blocked !== null}
      >
        <SelectTrigger id={id} aria-label={label} className='w-full'>
          <SelectValue placeholder={placeholder} />
        </SelectTrigger>
        <SelectContent>
          {Object.entries(table).map(([key, text]) => (
            <SelectItem key={key} value={key}>
              {text}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </FieldTile>
  )
}

export function ControlPanel({
  title,
  note,
  hold,
  onHold,
  children,
  act,
}: {
  title: string
  note: string
  hold?: boolean
  onHold?: (value: boolean) => void
  children: ReactNode
  act?: ActProp
}) {
  return (
    <div className='flex min-w-0 flex-col gap-4 rounded-md p-3 sealed-well'>
      <div className='flex min-w-0 flex-wrap items-center justify-between gap-3'>
        <div className='flex min-w-0 flex-col gap-0.5'>
          <Text weight='semibold'>{title}</Text>
          <Muted variant='caption'>{note}</Muted>
        </div>
        {onHold && (
          <label className='flex shrink-0 items-center gap-2'>
            <Switch
              permission='lock_canon'
              act={act}
              checked={hold ?? false}
              onCheckedChange={onHold}
              aria-label='Hold what I set'
            />
            <Text as='span'>Hold what I set</Text>
          </label>
        )}
      </div>
      {children}
    </div>
  )
}

const PLURALS: Record<string, string> = {
  mortal: 'mortals',
  settlement: 'settlements',
  people: 'peoples',
  polity: 'realms',
  house: 'houses',
  faction: 'factions',
  cult: 'cults',
  region: 'regions',
  place: 'places',
  prophecy: 'prophecies',
  artifact: 'artifacts',
}

export function NodePicker({
  label,
  types,
  value,
  onChange,
  blocked,
  act,
}: {
  label: string
  types: string[]
  value: number | null
  onChange: (value: number | null) => void
  blocked: string | null
  act?: ActProp
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
  const kinds = [...new Set(types.map((type) => PLURALS[type] ?? `${type}s`))]
  return (
    <FieldTile id={id} label={label}>
      <RecordCombobox
        act={act}
        id={id}
        options={options}
        value={value === null ? null : String(value)}
        onChange={(next) => onChange(next === null ? null : Number(next))}
        placeholder={`Search ${kinds.slice(0, 2).join(' or ')}${kinds.length > 2 ? ' and more' : ''}`}
        disabled={blocked !== null}
        disabledReason={blocked ?? undefined}
        clearable
        aria-label={label}
      />
    </FieldTile>
  )
}

export function FormBar({
  children,
  action,
}: {
  children: ReactNode
  action: ReactNode
}) {
  return (
    <div className='flex min-w-0 flex-col gap-3 @lg/mind:flex-row @lg/mind:items-end'>
      <div className='grid min-w-0 flex-1 grid-cols-1 gap-3 @lg/mind:auto-cols-fr @lg/mind:grid-flow-col'>
        {children}
      </div>
      <div className='flex shrink-0 justify-end'>{action}</div>
    </div>
  )
}

export function AddBar({
  title,
  children,
  action,
}: {
  title: string
  children: ReactNode
  action: ReactNode
}) {
  return (
    <div className='flex min-w-0 flex-col gap-3 border-t pt-4'>
      <Label variant='overline'>{title}</Label>
      <FormBar action={action}>{children}</FormBar>
    </div>
  )
}

export function ItemRow({
  icon,
  tone,
  title,
  meta,
  badges,
  actions,
  children,
  editor,
  editLabel,
}: {
  icon: LucideIcon
  tone?: KpiTone
  title: ReactNode
  meta?: ReactNode
  badges?: ReactNode
  actions?: ReactNode
  children?: ReactNode
  editor?: ReactNode
  editLabel?: string
}) {
  const [open, setOpen] = useState(false)
  return (
    <div className='flex min-w-0 flex-col gap-3 rounded-md border surface-well border-gild/20 bg-muted/60 p-3'>
      <div className='flex min-w-0 flex-wrap items-start gap-3'>
        <Medallion icon={icon} tone={tone} size='sm' />
        <div className='flex min-w-0 flex-1 basis-36 flex-col gap-1'>
          <div className='flex min-w-0 flex-wrap items-center gap-2'>
            <Text weight='semibold' truncate>
              {title}
            </Text>
            {badges}
          </div>
          {meta && <Muted variant='caption'>{meta}</Muted>}
        </div>
        <div className='flex shrink-0 flex-wrap items-center justify-end gap-1'>
          {actions}
          {editor && (
            <Button
              size='icon-sm'
              variant={open ? 'secondary' : 'ghost'}
              aria-label={
                open
                  ? `Close ${editLabel ?? 'the editor'}`
                  : `Open ${editLabel ?? 'the editor'}`
              }
              aria-expanded={open}
              onClick={() => setOpen((value) => !value)}
            >
              {open ? <ChevronUp /> : <ChevronDown />}
            </Button>
          )}
        </div>
      </div>
      {children}
      {editor && open && (
        <div className='flex min-w-0 flex-col gap-4 rounded-md p-3 sealed-well'>
          {editor}
        </div>
      )}
    </div>
  )
}

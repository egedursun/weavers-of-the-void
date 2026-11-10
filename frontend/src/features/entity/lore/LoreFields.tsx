import { type ReactNode, useId, useState } from 'react'
import {
  Check,
  Lock,
  Plus,
  Save,
  SlidersHorizontal,
  Trash2,
  Unlock,
  type LucideIcon,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Input } from '@/components/ui/input'
import { Progress, type ProgressTone } from '@/components/ui/progress'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import {
  ChangeChip,
  EntityLink,
  type KpiTone,
  Medallion,
  PagedList,
} from '@/components/domain'
import { Label, Muted, SectionTitle, Stat, Text } from '@/components/typography'
import { type LoreValue } from './api'
import {
  type LoreNamed,
  PERCENT,
  busyOf,
  fieldLabel,
  lookup,
  useLoreEdit,
} from './model'

export type FieldSpec =
  | {
      key: string
      kind: 'number'
      min?: number
      max?: number
      nullable?: boolean
    }
  | { key: string; kind: 'bool' }
  | { key: string; kind: 'text'; nullable?: boolean }
  | {
      key: string
      kind: 'enum'
      table?: Record<string, LoreNamed>
      values?: readonly string[]
    }
  | { key: string; kind: 'record'; table: Record<string, LoreNamed> }

export const NO_RECORD = 'none'

export type Editor = {
  mutate: (variables: {
    values: Record<string, unknown>
    release?: string[]
  }) => void
  isPending: boolean
}

export type DictSpec = {
  key: string
  label: string
  value: Record<string, number | string>
}

type Ref = { id: number; name: string } | null | undefined

const BADGE_TONE: Record<
  KpiTone,
  'default' | 'info' | 'success' | 'warning' | 'destructive' | 'secondary'
> = {
  gold: 'default',
  verdigris: 'info',
  info: 'info',
  success: 'success',
  warning: 'warning',
  danger: 'destructive',
  muted: 'secondary',
}

const TEXT_TONE: Record<KpiTone, string> = {
  gold: 'text-primary',
  verdigris: 'text-brand-verdigris',
  info: 'text-info',
  success: 'text-success',
  warning: 'text-warning',
  danger: 'text-destructive',
  muted: 'text-muted-foreground',
}

const BAR_TONE: Record<KpiTone, ProgressTone> = {
  gold: 'default',
  verdigris: 'verdigris',
  info: 'info',
  success: 'success',
  warning: 'warning',
  danger: 'destructive',
  muted: 'muted',
}

export function MeterList({
  surface,
  children,
}: {
  surface: string
  children: ReactNode
}) {
  return (
    <ul
      data-surface={surface}
      className='grid min-w-0 grid-cols-1 gap-2 @xl/lore:grid-cols-2'
    >
      {children}
    </ul>
  )
}

export function MeterRow({
  item,
  label,
  value,
  max = PERCENT,
  unit = '%',
  icon: Icon,
  tone,
  children,
}: {
  item: Ref
  label: string
  value: number
  max?: number
  unit?: string
  icon: LucideIcon
  tone: KpiTone
  children?: ReactNode
}) {
  return (
    <li className='flex min-w-0 flex-col gap-1.5 rounded-md border bg-muted/30 px-2.5 py-2 @xl/lore:last:odd:col-span-2'>
      <div className='flex min-w-0 items-center gap-2'>
        <Icon
          aria-hidden='true'
          className={cn('size-icon-sm shrink-0', TEXT_TONE[tone])}
        />
        <Text as='span' weight='medium' className='min-w-0 flex-1' truncate>
          <Who item={item} />
        </Text>
        <Stat value={value} unit={unit} />
      </div>
      <Progress
        value={max > 0 ? Math.min(PERCENT, (value / max) * PERCENT) : 0}
        size='sm'
        tone={BAR_TONE[tone]}
        aria-label={`${item?.name ?? 'Unknown'} ${label}`}
      />
      <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
        {children}
        <Muted as='span' variant='caption'>
          {label}
        </Muted>
      </div>
    </li>
  )
}

export function Who({
  item,
  fallback = 'unknown',
}: {
  item: Ref
  fallback?: string
}) {
  if (!item) return <Muted as='span'>{fallback}</Muted>
  return (
    <EntityLink kind='entity' id={String(item.id)}>
      {item.name}
    </EntityLink>
  )
}

export function NamedChip({
  spec,
  children,
}: {
  spec: LoreNamed
  children?: ReactNode
}) {
  const Icon = spec.icon
  return (
    <Badge variant={BADGE_TONE[spec.tone]}>
      <Icon aria-hidden='true' />
      {children ?? spec.label}
    </Badge>
  )
}

export function LoreHero({
  spec,
  kicker,
  title,
  hint,
  children,
}: {
  spec: LoreNamed
  kicker: string
  title?: string
  hint?: string
  children?: ReactNode
}) {
  return (
    <div
      data-surface='LoreHero'
      className='relative flex min-w-0 items-start gap-3 overflow-hidden rounded-xl border bg-background p-4'
    >
      <Medallion icon={spec.icon} tone={spec.tone} />
      <div className='flex min-w-0 flex-1 flex-col gap-2'>
        <div className='flex min-w-0 flex-col gap-0.5'>
          <Label variant='overline'>{kicker}</Label>
          <SectionTitle level={3}>{title ?? spec.label}</SectionTitle>
          {(hint ?? spec.hint) && <Muted>{hint ?? spec.hint}</Muted>}
        </div>
        {children && (
          <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
            {children}
          </div>
        )}
      </div>
    </div>
  )
}

export function RefChip({
  icon: Icon,
  label,
  item,
}: {
  icon: LucideIcon
  label: string
  item: Ref
}) {
  if (!item) return null
  return (
    <Text
      as='span'
      variant='caption'
      className='inline-flex h-badge-md max-w-full min-w-0 items-center gap-1.5 rounded-md border bg-muted/40 px-2'
    >
      <Icon
        aria-hidden='true'
        className='size-icon-xs shrink-0 text-muted-foreground'
      />
      {label && <span className='shrink-0 text-muted-foreground'>{label}</span>}
      <Who item={item} />
    </Text>
  )
}

export function LoreCard({
  title,
  icon,
  tone = 'gold',
  aside,
  wide,
  children,
}: {
  title: string
  icon: LucideIcon
  tone?: KpiTone
  aside?: ReactNode
  wide?: boolean
  children: ReactNode
}) {
  return (
    <div
      data-surface='LoreCard'
      className={cn(
        'flex h-full min-w-0 flex-col gap-3 rounded-lg border bg-background p-3',
        wide && '@xl/lore:col-span-2'
      )}
    >
      <div className='flex min-w-0 items-center gap-2'>
        <Medallion icon={icon} tone={tone} size='sm' />
        <Label variant='overline' className='min-w-0 flex-1' truncate>
          {title}
        </Label>
        {aside}
      </div>
      {children}
    </div>
  )
}

export function RoleRow({
  icon,
  tone = 'muted',
  label,
  children,
}: {
  icon: LucideIcon
  tone?: KpiTone
  label: string
  children: ReactNode
}) {
  return (
    <div className='flex min-w-0 items-center gap-2.5'>
      <Medallion icon={icon} tone={tone} size='sm' />
      <div className='flex min-w-0 flex-1 flex-col'>
        <Label>{label}</Label>
        <div className='min-w-0'>{children}</div>
      </div>
    </div>
  )
}

export function ShiftChips({
  entries,
  table,
  empty,
}: {
  entries: Record<string, number | string>
  table: Record<string, LoreNamed>
  empty: string
}) {
  const rows = Object.entries(entries).sort(
    ([, left], [, right]) => Math.abs(Number(right)) - Math.abs(Number(left))
  )
  if (rows.length === 0) return <Muted>{empty}</Muted>
  return (
    <PagedList
      items={rows}
      initial={12}
      noun={['entry', 'entries']}
      as='ul'
      className='flex min-w-0 flex-wrap gap-1.5'
      itemKey={([key]) => key}
    >
      {([key, value]) => {
        const spec = lookup(table, key)
        return (
          <li key={key}>
            <ChangeChip
              value={Number(value) || 0}
              label={spec.label}
              icon={spec.icon}
            />
          </li>
        )
      }}
    </PagedList>
  )
}

export function TermChips({
  entries,
  table,
  empty,
  tone,
  unit,
}: {
  entries: Record<string, number | string>
  table: Record<string, LoreNamed>
  empty: string
  tone?: KpiTone
  unit?: (key: string, value: number | string) => string
}) {
  const rows = Object.entries(entries)
  if (rows.length === 0) return <Muted>{empty}</Muted>
  return (
    <PagedList
      items={rows}
      initial={12}
      noun={['entry', 'entries']}
      as='ul'
      className='flex min-w-0 flex-wrap gap-1.5'
      itemKey={([key]) => key}
    >
      {([key, value]) => {
        const spec = lookup(table, key)
        return (
          <li key={key}>
            <NamedChip spec={tone ? { ...spec, tone } : spec}>
              {unit ? unit(key, value) : `${value} ${spec.label.toLowerCase()}`}
            </NamedChip>
          </li>
        )
      }}
    </PagedList>
  )
}

export function ChoicePicker({
  label,
  value,
  table,
  blocked,
  placeholder,
  onPick,
}: {
  label: string
  value: string
  table: Record<string, LoreNamed>
  blocked: string | null
  placeholder?: string
  onPick: (value: string) => void
}) {
  return (
    <div className='flex min-w-0 flex-col gap-1'>
      <Label>{label}</Label>
      <ChoiceSelect
        label={label}
        value={value}
        table={table}
        blocked={blocked}
        placeholder={placeholder}
        onPick={onPick}
      />
    </div>
  )
}

export function ChoiceSelect({
  id,
  label,
  value,
  table,
  blocked,
  placeholder,
  onPick,
}: {
  id?: string
  label: string
  value: string
  table: Record<string, LoreNamed>
  blocked: string | null
  placeholder?: string
  onPick: (value: string) => void
}) {
  return (
    <Select value={value} onValueChange={onPick} disabled={blocked !== null}>
      <SelectTrigger id={id} aria-label={label} className='w-full'>
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent>
        {Object.entries(table).map(([key, spec]) => {
          const Icon = spec.icon
          return (
            <SelectItem key={key} value={key}>
              <Icon aria-hidden='true' />
              {spec.label}
            </SelectItem>
          )
        })}
      </SelectContent>
    </Select>
  )
}

export function AdjustBlock({
  title,
  icon: Icon,
  children,
}: {
  title: string
  icon: LucideIcon
  children: ReactNode
}) {
  return (
    <div className='flex min-w-0 flex-col gap-3 rounded-lg border bg-background p-3'>
      <div className='flex min-w-0 items-center gap-2'>
        <Icon
          aria-hidden='true'
          className='size-icon-sm shrink-0 text-primary'
        />
        <Label variant='overline'>{title}</Label>
      </div>
      {children}
    </div>
  )
}

export function AdjustPanel({
  surface,
  title,
  note,
  status,
  children,
}: {
  surface: string
  title: string
  note: string
  status?: ReactNode
  children: ReactNode
}) {
  return (
    <Collapsible data-surface={surface} className='flex min-w-0 flex-col gap-3'>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <CollapsibleTrigger asChild>
          <Button variant='outline'>
            <SlidersHorizontal />
            {title}
          </Button>
        </CollapsibleTrigger>
        {status}
      </div>
      <CollapsibleContent className='flex min-w-0 flex-col gap-3 rounded-lg border border-dashed bg-muted/20 p-3'>
        <div className='flex min-w-0 flex-col gap-0.5'>
          <Text weight='semibold'>{title}</Text>
          <Muted variant='caption'>{note}</Muted>
        </div>
        {children}
      </CollapsibleContent>
    </Collapsible>
  )
}

export function LoreAdjust({
  entityId,
  noun,
  locked,
  blocked,
  editor,
  children,
}: {
  entityId: number
  noun: string
  locked: readonly string[]
  blocked: string | null
  editor?: Editor
  children: ReactNode
}) {
  const own = useLoreEdit(entityId)
  const edit = editor ?? own
  const busy = busyOf(blocked, edit.isPending)
  return (
    <AdjustPanel
      surface='LoreAdjust'
      title={`Shape this ${noun}`}
      note='Every value above can be set here. A value you set is held: the world stops moving it until you let it decide again. Every change goes into the ledger and can be undone.'
      status={
        locked.length > 0 && (
          <Badge variant='default'>
            <Lock aria-hidden='true' />
            {`${locked.length} held by you`}
          </Badge>
        )
      }
    >
      {locked.length > 0 && (
        <div className='flex min-w-0 flex-col gap-2'>
          <PagedList
            items={locked}
            initial={12}
            noun={['entry', 'entries']}
            as='div'
            className='flex min-w-0 flex-wrap items-center gap-2'
            listProps={{ 'data-surface': 'LoreHeld' }}
            itemKey={(key) => key}
          >
            {(key) => (
              <Badge key={key} variant='default'>
                <Lock aria-hidden='true' />
                {`Held: ${fieldLabel(key).toLowerCase()}`}
              </Badge>
            )}
          </PagedList>
          <div className='flex min-w-0 flex-wrap items-center gap-2'>
            <Button
              size='sm'
              variant='outline'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => edit.mutate({ values: {}, release: [...locked] })}
            >
              <Unlock />
              Let the world decide again
            </Button>
          </div>
        </div>
      )}
      {children}
    </AdjustPanel>
  )
}

function tableOf(values: readonly string[]): Record<string, LoreNamed> {
  return Object.fromEntries(values.map((value) => [value, lookup({}, value)]))
}

function shown(value: unknown): string {
  return value === null || value === undefined ? '' : String(value)
}

function parsed(spec: FieldSpec, raw: string | boolean): LoreValue {
  if (spec.kind === 'bool') return Boolean(raw)
  if (spec.kind === 'number') {
    if (raw === '' && spec.nullable) return null
    return Math.round(Number(raw) || 0)
  }
  if (spec.kind === 'text' && raw === '' && spec.nullable) return null
  if (spec.kind === 'record') return raw === NO_RECORD ? null : Number(raw)
  return String(raw)
}

function rangeOf(spec: FieldSpec): string {
  if (spec.kind !== 'number') return ''
  if (spec.min !== undefined && spec.max !== undefined)
    return ` (${spec.min}–${spec.max})`
  if (spec.min !== undefined) return ` (${spec.min}+)`
  return ''
}

export function LoreFields({
  entityId,
  surface,
  fields,
  current,
  locked = [],
  blocked,
  editor,
}: {
  entityId: number
  surface: string
  fields: readonly FieldSpec[]
  current: Readonly<Record<string, unknown>>
  locked?: readonly string[]
  blocked: string | null
  editor?: Editor
}) {
  const [draft, setDraft] = useState<Record<string, string | boolean>>(() =>
    Object.fromEntries(
      fields.map((spec) => [
        spec.key,
        spec.kind === 'bool'
          ? Boolean(current[spec.key])
          : spec.kind === 'record'
            ? shown(current[spec.key]) || NO_RECORD
            : shown(current[spec.key]),
      ])
    )
  )
  const id = useId()
  const own = useLoreEdit(entityId)
  const edit = editor ?? own
  const busy = busyOf(blocked, edit.isPending)
  const changed = fields.filter(
    (spec) => parsed(spec, draft[spec.key]) !== (current[spec.key] ?? null)
  )
  const save = () =>
    edit.mutate({
      values: Object.fromEntries(
        changed.map((spec) => [spec.key, parsed(spec, draft[spec.key])])
      ),
    })
  const put = (key: string, value: string | boolean) =>
    setDraft((before) => ({ ...before, [key]: value }))
  const choices = fields.filter(
    (spec) => spec.kind === 'enum' || spec.kind === 'record'
  )
  const values = fields.filter(
    (spec) => spec.kind === 'number' || spec.kind === 'text'
  )
  const flags = fields.filter((spec) => spec.kind === 'bool')
  return (
    <div
      data-surface={surface}
      className='@container/lore flex min-w-0 flex-col gap-3'
    >
      {choices.length > 0 && (
        <div className='grid min-w-0 grid-cols-1 gap-3 @md/lore:grid-cols-2 @3xl/lore:grid-cols-3'>
          {choices.map(
            (spec) =>
              (spec.kind === 'enum' || spec.kind === 'record') && (
                <ChoicePicker
                  key={spec.key}
                  label={fieldLabel(spec.key)}
                  value={String(draft[spec.key])}
                  table={
                    spec.kind === 'record'
                      ? spec.table
                      : (spec.table ?? tableOf(spec.values ?? []))
                  }
                  blocked={busy}
                  onPick={(value) => put(spec.key, value)}
                />
              )
          )}
        </div>
      )}
      {values.length > 0 && (
        <div className='grid min-w-0 grid-cols-1 gap-3 @xs/lore:grid-cols-2 @2xl/lore:grid-cols-3'>
          {values.map((spec) => (
            <div key={spec.key} className='flex min-w-0 flex-col gap-1'>
              <Label as='label' htmlFor={`${id}-${spec.key}`} truncate>
                {`${fieldLabel(spec.key)}${rangeOf(spec)}`}
              </Label>
              <Input
                id={`${id}-${spec.key}`}
                type={spec.kind === 'number' ? 'number' : 'text'}
                inputMode={spec.kind === 'number' ? 'numeric' : undefined}
                min={spec.kind === 'number' ? spec.min : undefined}
                max={spec.kind === 'number' ? spec.max : undefined}
                value={String(draft[spec.key])}
                aria-label={fieldLabel(spec.key)}
                onChange={(event) => put(spec.key, event.target.value)}
              />
            </div>
          ))}
        </div>
      )}
      {flags.length > 0 && (
        <div className='grid min-w-0 grid-cols-1 gap-2 @md/lore:grid-cols-2'>
          {flags.map((spec) => (
            <label
              key={spec.key}
              className='flex min-w-0 items-center justify-between gap-3 rounded-md border bg-muted/30 px-3 py-2'
            >
              <Text as='span'>{fieldLabel(spec.key)}</Text>
              <Switch
                checked={Boolean(draft[spec.key])}
                disabled={busy !== null}
                aria-label={fieldLabel(spec.key)}
                onCheckedChange={(next) => put(spec.key, next)}
              />
            </label>
          ))}
        </div>
      )}
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Button
          size='sm'
          disabled={busy !== null || changed.length === 0}
          disabledReason={
            busy ?? (changed.length === 0 ? 'Change a value first' : undefined)
          }
          onClick={save}
        >
          <Save />
          Set it so
        </Button>
        {changed.length > 0 && (
          <Muted as='span' variant='caption'>
            {`${changed.length} changed: ${changed.map((spec) => fieldLabel(spec.key).toLowerCase()).join(', ')}`}
          </Muted>
        )}
        {locked.length > 0 && (
          <>
            <Button
              size='sm'
              variant='outline'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => edit.mutate({ values: {}, release: [...locked] })}
            >
              <Unlock />
              Let the world decide again
            </Button>
            {locked.map((key) => (
              <Badge key={key} variant='default'>
                <Lock aria-hidden='true' />
                {`Held: ${fieldLabel(key).toLowerCase()}`}
              </Badge>
            ))}
          </>
        )}
      </div>
    </div>
  )
}

export function RowEditor({
  label,
  icon: Icon,
  value,
  min = 0,
  max,
  blocked,
  onSave,
  children,
}: {
  label: string
  icon?: LucideIcon
  value: number
  min?: number
  max?: number
  blocked: string | null
  onSave: (value: number) => void
  children?: ReactNode
}) {
  const [draft, setDraft] = useState(String(value))
  const id = useId()
  const next = Math.round(Number(draft))
  const problem =
    draft.trim() === '' || Number.isNaN(next)
      ? 'Give a whole number'
      : next < min || (max !== undefined && next > max)
        ? `Must be ${min}–${max ?? '…'}`
        : next === value
          ? 'This is the present value'
          : null
  const reason = blocked ?? problem
  return (
    <form
      className='flex min-w-0 items-end gap-2'
      onSubmit={(event) => {
        event.preventDefault()
        if (reason === null) onSave(next)
      }}
    >
      <div className='flex min-w-0 flex-1 flex-col gap-1'>
        <Label
          as='label'
          htmlFor={id}
          className='flex min-w-0 items-center gap-1.5'
        >
          {Icon && (
            <Icon aria-hidden='true' className='size-icon-xs shrink-0' />
          )}
          <span className='min-w-0'>
            {max === undefined ? label : `${label} (${min}–${max})`}
          </span>
        </Label>
        <Input
          id={id}
          type='number'
          inputMode='numeric'
          min={min}
          max={max}
          value={draft}
          aria-label={label}
          onChange={(event) => setDraft(event.target.value)}
        />
      </div>
      {children}
      <Button
        type='submit'
        size='icon'
        variant='outline'
        aria-label={`Set ${label}`}
        disabled={reason !== null}
        disabledReason={reason ?? undefined}
      >
        <Check />
      </Button>
    </form>
  )
}

export function RowEditors({ children }: { children: ReactNode }) {
  return (
    <div className='grid min-w-0 grid-cols-1 gap-3 @lg/lore:grid-cols-2'>
      {children}
    </div>
  )
}

export function DictField({
  entityId,
  spec,
  blocked,
  table,
  suggestions,
  editor,
}: {
  entityId: number
  spec: DictSpec
  blocked: string | null
  table?: Record<string, LoreNamed>
  suggestions?: readonly string[]
  editor?: Editor
}) {
  const known = table ?? tableOf(suggestions ?? [])
  const [rows, setRows] = useState<Array<[string, string]>>(() =>
    Object.entries(spec.value).map(([key, value]) => [key, String(value)])
  )
  const [fresh, setFresh] = useState('')
  const [typed, setTyped] = useState('')
  const own = useLoreEdit(entityId)
  const edit = editor ?? own
  const busy = busyOf(blocked, edit.isPending)
  const open = Object.fromEntries(
    Object.entries(known).filter(([key]) => !rows.some(([row]) => row === key))
  )
  const choosing = Object.keys(known).length > 0
  const entry = choosing ? fresh : typed.trim().replaceAll(' ', '_')
  const save = (next: Array<[string, string]>) =>
    edit.mutate({
      values: {
        [spec.key]: Object.fromEntries(
          next.map(([key, value]) => [
            key,
            Number.isNaN(Number(value)) ? value : Math.round(Number(value)),
          ])
        ),
      },
    })
  return (
    <div
      data-surface='LoreDictField'
      className='@container/lore flex min-w-0 flex-col gap-3'
    >
      {rows.length === 0 && <Muted>Nothing is set yet.</Muted>}
      <ul className='grid min-w-0 grid-cols-1 gap-2 @lg/lore:grid-cols-2'>
        {rows.map(([key, value], index) => {
          const named = lookup(known, key)
          const Icon = named.icon
          return (
            <li
              key={key}
              className='flex min-w-0 items-center gap-2 rounded-md border bg-muted/30 p-1.5 pl-2.5'
            >
              <Icon
                aria-hidden='true'
                className='size-icon-sm shrink-0 text-muted-foreground'
              />
              <Text as='span' className='min-w-0 flex-1' truncate>
                {named.label}
              </Text>
              <Input
                className='w-20 shrink-0'
                value={value}
                aria-label={named.label}
                onChange={(event) =>
                  setRows((before) =>
                    before.map((row, at) =>
                      at === index ? [row[0], event.target.value] : row
                    )
                  )
                }
              />
              <Button
                size='icon-sm'
                variant='ghost'
                aria-label={`Remove ${named.label}`}
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() => {
                  const next = rows.filter((_, at) => at !== index)
                  setRows(next)
                  save(next)
                }}
              >
                <Trash2 />
              </Button>
            </li>
          )
        })}
      </ul>
      <div className='flex min-w-0 flex-wrap items-end gap-2'>
        <div className='min-w-0 flex-1 basis-48'>
          {choosing ? (
            <ChoicePicker
              label={`Add to ${spec.label.toLowerCase()}`}
              value={fresh}
              table={open}
              blocked={busy}
              placeholder='Choose'
              onPick={setFresh}
            />
          ) : (
            <div className='flex min-w-0 flex-col gap-1'>
              <Label>{`Add to ${spec.label.toLowerCase()}`}</Label>
              <Input
                value={typed}
                aria-label='New entry'
                onChange={(event) => setTyped(event.target.value)}
              />
            </div>
          )}
        </div>
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null || entry === ''}
          disabledReason={
            busy ?? (entry === '' ? 'Name the entry first' : undefined)
          }
          onClick={() => {
            setRows((before) => [...before, [entry, '0']])
            setFresh('')
            setTyped('')
          }}
        >
          <Plus />
          Add
        </Button>
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => save(rows)}
        >
          <Save />
          Set it so
        </Button>
      </div>
    </div>
  )
}

import { type ReactNode, useId, useMemo, useState } from 'react'
import { Plus, SlidersHorizontal, X, type LucideIcon } from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Input } from '@/components/ui/input'
import {
  ChangeChip,
  EntityLink,
  FieldTile,
  type KpiTone,
  Medallion,
  Paged,
  PagedList,
} from '@/components/domain'
import { RecordCombobox } from '@/components/domain/RecordCombobox'
import { type EntryKind } from '@/components/layout/entry/entryStack'
import { Label, Muted, Stat, Text } from '@/components/typography'
import { useNames } from '../api/queries'
import { ControlPanel, FormBar, NodePicker } from '../mind/parts'
import { type Named, badgeVariant, plain } from './labels'

export function Panel({
  title,
  icon,
  tone = 'gold',
  hint,
  count,
  actions,
  children,
  className,
}: {
  title: string
  icon: LucideIcon
  tone?: KpiTone
  hint?: string
  count?: number
  actions?: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <div
      className={cn(
        'flex min-w-0 flex-col gap-3 rounded-md border surface-framed border-gild/70 bg-card p-3',
        className
      )}
    >
      <div className='flex min-w-0 items-center gap-2'>
        <Medallion icon={icon} tone={tone} size='sm' />
        <div className='flex min-w-0 flex-1 flex-col'>
          <div className='flex min-w-0 items-center gap-2'>
            <Label variant='overline' truncate>
              {title}
            </Label>
            {count !== undefined && (
              <Badge size='sm' variant='secondary'>
                {formatInteger(count)}
              </Badge>
            )}
          </div>
          {hint && (
            <Muted variant='caption' truncate>
              {hint}
            </Muted>
          )}
        </div>
        {actions && (
          <div className='flex shrink-0 items-center gap-1'>{actions}</div>
        )}
      </div>
      {children}
    </div>
  )
}

export function Hero({
  icon,
  tone,
  eyebrow,
  title,
  children,
}: {
  icon: LucideIcon
  tone?: KpiTone
  eyebrow: string
  title: ReactNode
  children?: ReactNode
}) {
  return (
    <div className='flex min-w-0 items-center gap-3 rounded-md border surface-framed border-gild/70 bg-card p-3'>
      <Medallion icon={icon} tone={tone ?? 'gold'} />
      <div className='flex min-w-0 flex-1 flex-col gap-1.5'>
        <div className='flex min-w-0 flex-col'>
          <Label variant='overline' truncate>
            {eyebrow}
          </Label>
          <Text as='div' weight='semibold' truncate={2}>
            {title}
          </Text>
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

export function Tag({ spec, text }: { spec: Named; text?: string }) {
  const Icon = spec.icon
  return (
    <Badge size='sm' variant={badgeVariant(spec.tone)}>
      <Icon aria-hidden='true' />
      {text ?? spec.label}
    </Badge>
  )
}

export function AdjustPanel({
  title,
  note,
  trigger = 'Adjust',
  hold,
  onHold,
  children,
}: {
  title: string
  note: string
  trigger?: string
  hold?: boolean
  onHold?: (value: boolean) => void
  children: ReactNode
}) {
  return (
    <Collapsible className='flex min-w-0 flex-col gap-3'>
      <CollapsibleTrigger asChild>
        <Button variant='outline' size='sm' className='self-start'>
          <SlidersHorizontal />
          {trigger}
        </Button>
      </CollapsibleTrigger>
      <CollapsibleContent className='flex min-w-0 flex-col'>
        <ControlPanel title={title} note={note} hold={hold} onHold={onHold}>
          {children}
        </ControlPanel>
      </CollapsibleContent>
    </Collapsible>
  )
}

export function RecordField({
  label,
  types,
  value,
  onChange,
  blocked,
  placeholder = 'Choose a record',
}: {
  label: string
  types: readonly string[] | null
  value: number | null
  onChange: (value: number | null) => void
  blocked: string | null
  placeholder?: string
}) {
  const id = useId()
  const names = useNames()
  const options = useMemo(
    () =>
      (names.data ?? [])
        .filter(
          (entry) =>
            entry.kind === 'entity' &&
            entry.status !== 'rejected' &&
            (types === null || types.includes(entry.type))
        )
        .map((entry) => ({
          value: String(entry.id),
          label: entry.name,
          hint: plain({}, entry.type),
          keywords: `#${entry.id}`,
        })),
    [names.data, types]
  )
  return (
    <FieldTile id={id} label={label}>
      <RecordCombobox
        id={id}
        options={options}
        value={value === null ? null : String(value)}
        onChange={(next) => onChange(next === null ? null : Number(next))}
        placeholder={names.isPending ? 'Reading the names…' : placeholder}
        disabled={blocked !== null}
        disabledReason={blocked ?? undefined}
        clearable
        aria-label={label}
      />
    </FieldTile>
  )
}

export function WhyList({ parts }: { parts: [string, number][] }) {
  return (
    <ul className='flex min-w-0 flex-col gap-1.5'>
      <Paged items={parts} as='li'>
        {([label, value]) => (
          <li key={label} className='flex min-w-0 items-center gap-2'>
            <Text as='span' className='min-w-0 flex-1' truncate>
              {plain({}, label)}
            </Text>
            <ChangeChip value={value} />
          </li>
        )}
      </Paged>
    </ul>
  )
}

export function ChoiceCard({
  spec,
  hint,
  selected,
  count,
  disabled = null,
  onSelect,
}: {
  spec: Named
  hint?: string
  selected: boolean
  count?: number
  disabled?: string | null
  onSelect: () => void
}) {
  const pick = () => {
    if (disabled === null) onSelect()
  }
  return (
    <div
      role='button'
      tabIndex={disabled === null ? 0 : -1}
      aria-pressed={selected}
      aria-disabled={disabled !== null}
      title={disabled ?? undefined}
      onClick={pick}
      onKeyDown={(event) => {
        if (event.key !== 'Enter' && event.key !== ' ') return
        event.preventDefault()
        pick()
      }}
      className={cn(
        'flex min-w-0 items-center gap-2 rounded-md border surface-sheen border-gild/60 bg-card p-2 transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring/50',
        disabled === null ? 'cursor-pointer hover:bg-accent/40' : 'opacity-60',
        selected ? 'border-primary/50 bg-primary/8' : 'bg-card'
      )}
    >
      <Medallion icon={spec.icon} tone={spec.tone ?? 'gold'} size='sm' />
      <div className='flex min-w-0 flex-1 flex-col'>
        <Text as='span' weight='medium' truncate>
          {spec.label}
        </Text>
        {hint && (
          <Muted as='span' variant='caption' truncate>
            {hint}
          </Muted>
        )}
      </div>
      {count !== undefined && <Stat value={count} size='kpi' />}
    </div>
  )
}

export function ChoiceGrid({
  label,
  table,
  value,
  hints,
  blocked,
  onPick,
}: {
  label: string
  table: Record<string, Named>
  value: string
  hints?: Record<string, string>
  blocked: string | null
  onPick: (value: string) => void
}) {
  return (
    <div
      role='group'
      aria-label={label}
      className='@container/choices flex min-w-0 flex-col gap-1.5'
    >
      <Label>{label}</Label>
      <div className='grid min-w-0 grid-cols-1 gap-2 @xs/choices:grid-cols-2 @xl/choices:grid-cols-3'>
        {Object.entries(table).map(([key, spec]) => (
          <ChoiceCard
            key={key}
            spec={spec}
            hint={hints?.[key]}
            selected={value === key}
            disabled={blocked}
            onSelect={() => onPick(key)}
          />
        ))}
      </div>
    </div>
  )
}

export function NumberField({
  label,
  icon: Icon,
  tone = 'text-muted-foreground',
  value,
  min,
  max,
  placeholder,
  blocked,
  onChange,
}: {
  label: string
  icon?: LucideIcon
  tone?: string
  value: string
  min?: number
  max?: number
  placeholder?: string
  blocked: string | null
  onChange: (value: string) => void
}) {
  const id = useId()
  return (
    <FieldTile id={id} label={label}>
      <div className='flex min-w-0 items-center gap-2'>
        {Icon && (
          <Icon
            aria-hidden='true'
            className={cn('size-icon-sm shrink-0', tone)}
          />
        )}
        <Input
          id={id}
          type='number'
          min={min}
          max={max}
          value={value}
          placeholder={placeholder}
          disabled={blocked !== null}
          className='min-w-0 flex-1'
          onChange={(event) => onChange(event.target.value)}
        />
      </div>
    </FieldTile>
  )
}

export function Fact({
  icon: Icon,
  label,
  children,
}: {
  icon: LucideIcon
  label: string
  children: ReactNode
}) {
  return (
    <div className='flex min-w-0 items-center gap-2'>
      <Icon
        aria-hidden='true'
        className='size-icon-sm shrink-0 text-muted-foreground'
      />
      <Label className='w-24 shrink-0' truncate>
        {label}
      </Label>
      <div className='flex min-w-0 flex-1 flex-wrap items-center gap-1.5'>
        {children}
      </div>
    </div>
  )
}

export function RefLink({
  node,
}: {
  node: { id: number; kind: string; name: string }
}) {
  const kind: EntryKind =
    node.kind === 'foreign_god'
      ? 'foreign-god'
      : node.kind === 'son' ||
          node.kind === 'world' ||
          node.kind === 'star' ||
          node.kind === 'creator'
        ? node.kind
        : 'entity'
  return (
    <EntityLink kind={kind} id={String(node.id)}>
      {node.name}
    </EntityLink>
  )
}

export function NodeListEditor({
  label,
  types,
  nodes,
  blocked,
  onChange,
}: {
  label: string
  types: string[]
  nodes: { id: number; kind: string; name: string }[]
  blocked: string | null
  onChange: (ids: number[]) => void
}) {
  const [adding, setAdding] = useState<number | null>(null)
  const ids = nodes.map((node) => node.id)
  const listed = adding !== null && ids.includes(adding)
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <Label variant='overline'>{label}</Label>
      {nodes.length === 0 ? (
        <Muted variant='caption'>None yet.</Muted>
      ) : (
        <PagedList
          items={nodes}
          initial={12}
          noun={['entry', 'entries']}
          as='div'
          className='flex min-w-0 flex-wrap items-center gap-1.5'
          itemKey={(node) => node.id}
        >
          {(node) => (
            <Badge key={node.id} variant='outline'>
              <RefLink node={node} />
              <Button
                size='icon-sm'
                variant='ghost'
                aria-label={`Remove ${node.name}`}
                disabled={blocked !== null}
                disabledReason={blocked ?? undefined}
                onClick={() => onChange(ids.filter((id) => id !== node.id))}
              >
                <X />
              </Button>
            </Badge>
          )}
        </PagedList>
      )}
      <FormBar
        action={
          <Button
            size='sm'
            variant='outline'
            disabled={blocked !== null || adding === null || listed}
            disabledReason={
              blocked ??
              (adding === null
                ? 'Choose one first.'
                : listed
                  ? 'Already listed.'
                  : undefined)
            }
            onClick={() => {
              if (adding === null) return
              onChange([...ids, adding])
              setAdding(null)
            }}
          >
            <Plus />
            Add
          </Button>
        }
      >
        <NodePicker
          label={`Add to ${label.toLowerCase()}`}
          types={types}
          value={adding}
          onChange={setAdding}
          blocked={blocked}
        />
      </FormBar>
    </div>
  )
}

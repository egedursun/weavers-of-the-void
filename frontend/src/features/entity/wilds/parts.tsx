import { Fragment, type ReactNode, useId, useState } from 'react'
import {
  ChevronDown,
  Lock,
  Plus,
  Save,
  SlidersHorizontal,
  Trash2,
  Unlock,
  type LucideIcon,
} from 'lucide-react'
import { domesticationStageValues } from '@/api/generated/schema'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { EntityLink, type KpiTone, Medallion } from '@/components/domain'
import { Label, Muted, Stat, Text } from '@/components/typography'
import { MindPicker } from '../mind/parts'
import { type Named, STAGE, named } from './labels'

export type Ref = { id: number; name: string } | null | undefined

const TRACK: Record<KpiTone, string> = {
  gold: 'fill-primary',
  verdigris: 'fill-brand-verdigris',
  info: 'fill-info',
  success: 'fill-success',
  warning: 'fill-warning',
  danger: 'fill-destructive',
  muted: 'fill-muted-foreground',
}

const FILL: Record<KpiTone, string> = {
  gold: 'bg-primary',
  verdigris: 'bg-brand-verdigris',
  info: 'bg-info',
  success: 'bg-success',
  warning: 'bg-warning',
  danger: 'bg-destructive',
  muted: 'bg-muted-foreground',
}

export function Name({ item, fallback }: { item: Ref; fallback?: string }) {
  if (!item) return <Muted as='span'>{fallback ?? 'Unknown'}</Muted>
  return (
    <EntityLink kind='entity' id={String(item.id)} showIcon>
      {item.name}
    </EntityLink>
  )
}

export function Card({
  title,
  icon,
  tone,
  hint,
  aside,
  wide,
  children,
}: {
  title: string
  icon: LucideIcon
  tone?: KpiTone
  hint?: string
  aside?: ReactNode
  wide?: boolean
  children: ReactNode
}) {
  return (
    <div
      className={cn(
        '@container/card flex h-full min-w-0 flex-col gap-3 rounded-lg border bg-background p-3',
        wide && '@xl/wild:col-span-2'
      )}
    >
      <div className='flex min-w-0 items-center gap-2'>
        <Medallion icon={icon} tone={tone} size='sm' />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Label variant='overline' truncate>
            {title}
          </Label>
          {hint && (
            <Muted variant='caption' truncate>
              {hint}
            </Muted>
          )}
        </div>
        {aside}
      </div>
      {children}
    </div>
  )
}

export function Tile({
  spec,
  caption,
  dim,
  aside,
}: {
  spec: Named
  caption?: ReactNode
  dim?: boolean
  aside?: ReactNode
}) {
  return (
    <div
      className={cn(
        'flex min-w-0 items-center gap-2 rounded-lg border p-2',
        dim ? 'border-dashed bg-transparent opacity-55' : 'bg-muted/30'
      )}
    >
      <Medallion
        icon={spec.icon}
        tone={dim ? 'muted' : (spec.tone ?? 'gold')}
        size='sm'
      />
      <div className='flex min-w-0 flex-1 flex-col'>
        <Text as='span' weight='medium' truncate>
          {spec.label}
        </Text>
        {caption && (
          <Muted as='span' variant='caption' truncate>
            {caption}
          </Muted>
        )}
      </div>
      {aside}
    </div>
  )
}

export function TileGrid({ children }: { children: ReactNode }) {
  return (
    <div className='grid min-w-0 grid-cols-1 gap-2 @sm/card:grid-cols-2 @xl/card:grid-cols-3'>
      {children}
    </div>
  )
}

export function RangeTrack({
  label,
  icon: Icon,
  low,
  high,
  floor,
  ceiling,
  tone = 'info',
  scale,
}: {
  label: string
  icon: LucideIcon
  low: number
  high: number
  floor: number
  ceiling: number
  tone?: KpiTone
  scale: string
}) {
  const span = Math.max(1, ceiling - floor)
  const start = ((Math.max(floor, Math.min(low, high)) - floor) / span) * 100
  const end = ((Math.min(ceiling, Math.max(low, high)) - floor) / span) * 100
  return (
    <div data-domain='range-track' className='flex min-w-0 flex-col gap-1.5'>
      <div className='flex min-w-0 items-center gap-2'>
        <Icon
          aria-hidden='true'
          className='size-icon-sm shrink-0 text-muted-foreground'
        />
        <Label truncate className='flex-1'>
          {label}
        </Label>
        <Stat value={`${low} – ${high}`} />
      </div>
      <svg
        role='img'
        aria-label={`${label} from ${low} to ${high}`}
        viewBox='0 0 100 1'
        preserveAspectRatio='none'
        className='h-meter-sm w-full overflow-hidden rounded-full'
      >
        <rect width='100' height='1' className='fill-muted' />
        <rect
          x={start}
          width={Math.max(2, end - start)}
          height='1'
          className={TRACK[tone]}
        />
      </svg>
      <div className='flex min-w-0 justify-between gap-2'>
        <Muted as='span' variant='caption'>
          {floor}
        </Muted>
        <Muted as='span' variant='caption' truncate>
          {scale}
        </Muted>
        <Muted as='span' variant='caption'>
          {ceiling}
        </Muted>
      </div>
    </div>
  )
}

export function StageTrack({ stage }: { stage: string }) {
  const current = named(STAGE, stage)
  const step = STAGE[stage]?.step ?? 0
  return (
    <div
      data-domain='stage-track'
      className='flex min-w-0 flex-col gap-2'
      aria-label={`Taming stage: ${current.label}`}
    >
      <div className='flex min-w-0 items-center'>
        {domesticationStageValues.map((key, index) => {
          const spec = named(STAGE, key)
          const reached = (STAGE[key]?.step ?? 0) <= step
          return (
            <Fragment key={key}>
              {index > 0 && (
                <span
                  aria-hidden='true'
                  className={cn(
                    'h-0.5 min-w-2 flex-1 rounded-full',
                    reached ? FILL[current.tone ?? 'gold'] : 'bg-border'
                  )}
                />
              )}
              <Tooltip>
                <TooltipTrigger asChild>
                  <span
                    tabIndex={0}
                    aria-label={spec.label}
                    className={cn(
                      'rounded-full',
                      key === stage &&
                        'ring-2 ring-ring/40 ring-offset-2 ring-offset-background'
                    )}
                  >
                    <Medallion
                      icon={spec.icon}
                      tone={reached ? (spec.tone ?? 'gold') : 'muted'}
                      size='sm'
                    />
                  </span>
                </TooltipTrigger>
                <TooltipContent className='flex flex-col gap-0.5'>
                  <Text as='span' weight='medium'>
                    {spec.label}
                  </Text>
                  <Muted variant='caption'>{STAGE[key]?.hint ?? ''}</Muted>
                </TooltipContent>
              </Tooltip>
            </Fragment>
          )
        })}
      </div>
      <div className='flex min-w-0 flex-wrap items-baseline gap-x-2'>
        <Text as='span' weight='semibold'>
          {current.label}
        </Text>
        <Muted as='span' variant='caption'>
          {STAGE[stage]?.hint ?? ''}
        </Muted>
      </div>
    </div>
  )
}

export function Held({
  keys,
  label,
  busy,
  onRelease,
}: {
  keys: readonly string[]
  label: (key: string) => string
  busy: string | null
  onRelease: () => void
}) {
  if (keys.length === 0) return null
  return (
    <div className='flex min-w-0 flex-wrap items-center gap-2'>
      <Lock aria-hidden='true' className='size-icon-xs shrink-0 text-primary' />
      {keys.map((key) => (
        <Badge key={key} size='sm' variant='default'>
          {`Held: ${label(key)}`}
        </Badge>
      ))}
      <Button
        size='sm'
        variant='outline'
        disabled={busy !== null}
        disabledReason={busy ?? undefined}
        onClick={onRelease}
      >
        <Unlock />
        Let the world decide again
      </Button>
    </div>
  )
}

export function AdjustPanel({
  title,
  note,
  label = 'Adjust',
  head,
  children,
}: {
  title: string
  note: string
  label?: string
  head?: ReactNode
  children: ReactNode
}) {
  return (
    <Collapsible className='flex min-w-0 flex-col gap-4 rounded-lg border border-dashed bg-muted/20 p-3'>
      <div className='flex min-w-0 flex-wrap items-center justify-between gap-3'>
        <div className='flex min-w-0 flex-1 basis-60 flex-col gap-0.5'>
          <Text weight='semibold'>{title}</Text>
          <Muted variant='caption'>{note}</Muted>
        </div>
        <CollapsibleTrigger asChild>
          <Button variant='outline' size='sm' className='group shrink-0'>
            <SlidersHorizontal />
            {label}
            <ChevronDown className='transition-transform group-aria-expanded:rotate-180' />
          </Button>
        </CollapsibleTrigger>
      </div>
      {head}
      <CollapsibleContent className='flex min-w-0 flex-col gap-4'>
        {children}
      </CollapsibleContent>
    </Collapsible>
  )
}

export function NumberField({
  label,
  value,
  min,
  max,
  disabled,
  onChange,
}: {
  label: string
  value: string
  min?: number
  max?: number
  disabled?: boolean
  onChange: (value: string) => void
}) {
  const id = useId()
  return (
    <div className='flex min-w-0 flex-col gap-1'>
      <Label as='label' htmlFor={id} truncate>
        {label}
      </Label>
      <Input
        id={id}
        type='number'
        inputMode='numeric'
        min={min}
        max={max}
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
      />
    </div>
  )
}

export function SwitchField({
  label,
  checked,
  disabled,
  onChange,
}: {
  label: string
  checked: boolean
  disabled?: boolean
  onChange: (value: boolean) => void
}) {
  const id = useId()
  return (
    <div className='flex min-w-0 flex-col gap-1'>
      <Label as='label' htmlFor={id} truncate>
        {label}
      </Label>
      <div className='flex h-control-md min-w-0 items-center gap-2'>
        <Switch
          id={id}
          checked={checked}
          disabled={disabled}
          onCheckedChange={onChange}
        />
        <Text as='span'>{checked ? 'Yes' : 'No'}</Text>
      </div>
    </div>
  )
}

export function Group({
  title,
  icon: Icon,
  wide,
  children,
}: {
  title: string
  icon: LucideIcon
  wide?: boolean
  children: ReactNode
}) {
  return (
    <div
      className={cn(
        'flex min-w-0 flex-col gap-3 rounded-lg border bg-background p-3',
        wide && '@xl/wild:col-span-2'
      )}
    >
      <div className='flex min-w-0 items-center gap-2'>
        <Icon aria-hidden='true' className='size-icon-sm text-primary' />
        <Label variant='overline'>{title}</Label>
      </div>
      {children}
    </div>
  )
}

export function ShareEditor({
  table,
  value,
  max,
  amount,
  busy,
  addLabel,
  onSave,
}: {
  table: Record<string, Named>
  value: Record<string, number | string>
  max?: number
  amount: string
  busy: string | null
  addLabel: string
  onSave: (next: Record<string, number>) => void
}) {
  const [rows, setRows] = useState<Array<[string, string]>>(() =>
    Object.entries(value).map(([key, share]) => [key, String(share)])
  )
  const [fresh, setFresh] = useState('')
  const whole = (next: Array<[string, string]>) =>
    Object.fromEntries(
      next.map(([key, share]) => [key, Math.round(Number(share) || 0)])
    )
  const left = Object.fromEntries(
    Object.entries(table)
      .filter(([key]) => !rows.some(([held]) => held === key))
      .map(([key, spec]) => [key, spec.label])
  )
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      {rows.length === 0 ? (
        <Muted>Nothing yet.</Muted>
      ) : (
        <Muted variant='caption'>{`Each number is ${amount}.`}</Muted>
      )}
      <ul className='grid min-w-0 grid-cols-1 gap-2 @xl/wild:grid-cols-2'>
        {rows.map(([key, share], index) => {
          const spec = named(table, key)
          return (
            <li
              key={key}
              className='flex min-w-0 items-center gap-2 rounded-lg border bg-muted/30 p-2'
            >
              <Medallion icon={spec.icon} tone={spec.tone} size='sm' />
              <Text as='span' weight='medium' truncate className='flex-1'>
                {spec.label}
              </Text>
              <Input
                className='w-20'
                type='number'
                inputMode='numeric'
                min={0}
                max={max}
                value={share}
                aria-label={spec.label}
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
                aria-label={`Remove ${spec.label}`}
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() => {
                  const next = rows.filter((_, at) => at !== index)
                  setRows(next)
                  onSave(whole(next))
                }}
              >
                <Trash2 />
              </Button>
            </li>
          )
        })}
      </ul>
      <div className='flex min-w-0 flex-wrap items-end gap-2'>
        <MindPicker
          label={addLabel}
          value={fresh}
          table={left}
          blocked={busy}
          placeholder='Choose'
          onPick={setFresh}
        />
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null || fresh === ''}
          disabledReason={
            busy ?? (fresh === '' ? 'Choose one first' : undefined)
          }
          onClick={() => {
            setRows((before) => [...before, [fresh, '0']])
            setFresh('')
          }}
        >
          <Plus />
          Add
        </Button>
        <Button
          size='sm'
          className='ml-auto'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => onSave(whole(rows))}
        >
          <Save />
          Set it so
        </Button>
      </div>
    </div>
  )
}

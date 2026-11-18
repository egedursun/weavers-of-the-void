import { type ReactNode, useId, useState } from 'react'
import {
  ChevronDown,
  ChevronUp,
  type LucideIcon,
  SlidersHorizontal,
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
import { Progress } from '@/components/ui/progress'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import {
  FieldTile,
  type KpiTone,
  Medallion,
  PagedList,
} from '@/components/domain'
import { Label, Muted, Stat, Text } from '@/components/typography'
import { ControlPanel } from '@/features/entity/mind/parts'
import {
  BADGE_TONE,
  type Named,
  PERCENT,
  frameTone,
  iconTone,
  named,
} from './labels'

const PIP_TONE: Record<KpiTone, string> = {
  gold: 'bg-primary',
  verdigris: 'bg-brand-verdigris',
  info: 'bg-info',
  success: 'bg-success',
  warning: 'bg-warning',
  danger: 'bg-destructive',
  muted: 'bg-muted-foreground',
}

export function Tag({
  item,
  text,
  size = 'sm',
}: {
  item: Named
  text?: string
  size?: 'sm' | 'default'
}) {
  const Icon = item.icon
  return (
    <Badge size={size} variant={BADGE_TONE[item.tone ?? 'muted']}>
      <Icon />
      {text ?? item.label}
    </Badge>
  )
}

export function TableTag({
  table,
  value,
  text,
}: {
  table: Record<string, Named>
  value: string
  text?: string
}) {
  return <Tag item={named(table, value)} text={text} />
}

export function Plain({
  icon: Icon,
  children,
}: {
  icon: LucideIcon
  children: ReactNode
}) {
  return (
    <Badge size='sm' variant='outline'>
      <Icon />
      {children}
    </Badge>
  )
}

export function Panel({
  title,
  icon,
  tone = 'gold',
  count,
  hint,
  actions,
  children,
}: {
  title: string
  icon: LucideIcon
  tone?: KpiTone
  count?: number
  hint?: string
  actions?: ReactNode
  children: ReactNode
}) {
  return (
    <div className='flex min-w-0 flex-col gap-3 rounded-md border surface-framed border-gild/70 bg-card p-4'>
      <div className='flex min-w-0 items-center gap-3'>
        <Medallion icon={icon} tone={tone} size='sm' />
        <div className='flex min-w-0 flex-1 flex-col'>
          <div className='flex min-w-0 items-center gap-2'>
            <Label variant='overline' truncate>
              {title}
            </Label>
            {count !== undefined && (
              <Badge size='sm' variant='secondary'>
                {count}
              </Badge>
            )}
          </div>
          {hint && (
            <Muted variant='caption' truncate>
              {hint}
            </Muted>
          )}
        </div>
        {actions}
      </div>
      {children}
    </div>
  )
}

export function Adjust({
  title,
  note,
  label = 'Adjust',
  children,
}: {
  title: string
  note: string
  label?: string
  children: ReactNode
}) {
  const [open, setOpen] = useState(false)
  return (
    <Collapsible
      open={open}
      onOpenChange={setOpen}
      className='flex min-w-0 flex-col gap-3'
    >
      <CollapsibleTrigger asChild>
        <Button variant='outline' size='sm' className='self-start'>
          <SlidersHorizontal />
          {label}
          {open ? <ChevronUp /> : <ChevronDown />}
        </Button>
      </CollapsibleTrigger>
      <CollapsibleContent className='min-w-0'>
        <ControlPanel title={title} note={note}>
          {children}
        </ControlPanel>
      </CollapsibleContent>
    </Collapsible>
  )
}

export function FieldGrid({ children }: { children: ReactNode }) {
  return (
    <div className='grid min-w-0 grid-cols-1 gap-2 @sm/mil:grid-cols-2 @3xl/mil:grid-cols-4'>
      {children}
    </div>
  )
}

export function NumberField({
  label,
  icon,
  value,
  onChange,
  max,
  min = 0,
  framed = true,
}: {
  label: string
  icon?: LucideIcon
  value: string
  onChange: (value: string) => void
  max?: number
  min?: number
  framed?: boolean
}) {
  const id = useId()
  return (
    <FieldTile
      id={id}
      label={label}
      icon={icon}
      framed={framed}
      aside={max === undefined ? `${min}+` : `${min}–${max}`}
    >
      <Input
        id={id}
        type='number'
        inputMode='numeric'
        min={min}
        max={max}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </FieldTile>
  )
}

export function ChoiceField({
  label,
  icon,
  value,
  table,
  blocked,
  onPick,
}: {
  label: string
  icon?: LucideIcon
  value: string
  table: Record<string, Named>
  blocked: string | null
  onPick: (value: string) => void
}) {
  const id = useId()
  return (
    <FieldTile id={id} label={label} icon={icon}>
      <Select value={value} onValueChange={onPick} disabled={blocked !== null}>
        <SelectTrigger id={id} aria-label={label} className='w-full'>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {Object.entries(table).map(([key, item]) => {
            const Icon = item.icon
            return (
              <SelectItem key={key} value={key}>
                <Icon aria-hidden='true' className={iconTone(item.tone)} />
                {item.label}
              </SelectItem>
            )
          })}
        </SelectContent>
      </Select>
    </FieldTile>
  )
}

export function ToggleField({
  item,
  checked,
  disabled,
  onChange,
}: {
  item: Named
  checked: boolean
  disabled: boolean
  onChange: (next: boolean) => void
}) {
  const Icon = item.icon
  return (
    <label
      className={cn(
        'flex min-w-0 cursor-pointer items-center gap-2 rounded-md border surface-sheen border-gild/60 bg-card p-2.5 transition-colors',
        checked ? frameTone(item.tone) : 'bg-card'
      )}
    >
      <Icon
        aria-hidden='true'
        className={cn(
          'size-icon-sm shrink-0',
          checked ? iconTone(item.tone) : 'text-muted-foreground'
        )}
      />
      <Text as='span' className='min-w-0 flex-1' truncate>
        {item.label}
      </Text>
      <Switch
        checked={checked}
        disabled={disabled}
        aria-label={item.label}
        onCheckedChange={onChange}
      />
    </label>
  )
}

export function Pips({
  value,
  max,
  tone = 'gold',
  label,
}: {
  value: number
  max: number
  tone?: KpiTone
  label: string
}) {
  return (
    <span
      role='meter'
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={max}
      aria-valuenow={value}
      className='inline-flex shrink-0 items-center gap-0.5'
    >
      {Array.from({ length: max }, (_, index) => (
        <span
          key={index}
          className={cn(
            'h-meter-md w-icon-xs rounded-sm',
            index < value ? PIP_TONE[tone] : 'bg-muted'
          )}
        />
      ))}
    </span>
  )
}

export function TugBar({
  left,
  right,
  value,
  scale,
  label,
}: {
  left: string
  right: string
  value: number
  scale: number
  label: string
}) {
  const share =
    PERCENT / 2 + (Math.max(-scale, Math.min(scale, value)) / scale) * 50
  return (
    <div className='flex min-w-0 flex-col gap-1.5'>
      <div className='flex min-w-0 items-center justify-between gap-2'>
        <Muted as='span' variant='caption' truncate>
          {left}
        </Muted>
        <Stat
          value={`${value > 0 ? '+' : ''}${value}`}
          unit={label}
          className='shrink-0'
        />
        <Muted as='span' variant='caption' truncate className='text-end'>
          {right}
        </Muted>
      </div>
      <Progress
        value={share}
        tone='destructive'
        className='bg-info'
        aria-label={label}
      />
    </div>
  )
}

export function Steps({
  table,
  value,
  label,
}: {
  table: Record<string, Named>
  value: string
  label: string
}) {
  const keys = Object.keys(table)
  const reached = keys.indexOf(value)
  return (
    <PagedList
      items={keys}
      initial={12}
      noun={['entry', 'entries']}
      as='ol'
      className='flex min-w-0 flex-wrap items-center gap-1'
      listProps={{ 'aria-label': label }}
      itemKey={(key) => key}
    >
      {(key, index) => {
        const item = table[key]
        const Icon = item.icon
        const on = index <= reached
        return (
          <li
            key={key}
            aria-current={index === reached ? 'step' : undefined}
            className={cn(
              'flex h-badge-md min-w-0 items-center gap-1 rounded-md border surface-sheen border-gild/60 bg-card px-2',
              on ? frameTone(item.tone) : 'border-dashed'
            )}
          >
            <Icon
              aria-hidden='true'
              className={cn(
                'size-icon-xs shrink-0',
                on ? iconTone(item.tone) : 'text-muted-foreground'
              )}
            />
            <Text
              as='span'
              variant='caption'
              weight={index === reached ? 'semibold' : 'normal'}
              tone={on ? 'default' : 'muted'}
            >
              {item.label}
            </Text>
          </li>
        )
      }}
    </PagedList>
  )
}

export function Quiet({
  items,
}: {
  items: { icon: LucideIcon; text: string }[]
}) {
  if (items.length === 0) return null
  return (
    <div className='flex min-w-0 flex-wrap items-center gap-2 rounded-md p-3 sealed-well'>
      <Label variant='overline'>Quiet</Label>
      {items.map((item) => (
        <Plain key={item.text} icon={item.icon}>
          {item.text}
        </Plain>
      ))}
    </div>
  )
}

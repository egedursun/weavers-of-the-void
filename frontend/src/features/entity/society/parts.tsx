import { type ReactNode, useId, useState } from 'react'
import {
  Check,
  ChevronDown,
  Lock,
  SlidersHorizontal,
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
import { Label as FieldLabel } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { type KpiTone, Medallion } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { type Spec } from './labels'
import { PIP_TONE, WORKING } from './tones'

export function Panel({
  title,
  icon,
  tone = 'gold',
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
        'flex h-full min-w-0 flex-col gap-3 rounded-lg border bg-background p-3',
        wide && 'col-span-full'
      )}
    >
      <div className='flex min-w-0 items-center gap-2.5'>
        <Medallion icon={icon} tone={tone} size='sm' />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Label variant='overline' truncate>
            {title}
          </Label>
          {hint && (
            <Muted variant='caption' truncate={2}>
              {hint}
            </Muted>
          )}
        </div>
        {aside && (
          <div className='flex shrink-0 items-center gap-1.5'>{aside}</div>
        )}
      </div>
      {children}
    </div>
  )
}

export function AdjustPanel({
  title,
  note,
  children,
}: {
  title: string
  note: string
  children: ReactNode
}) {
  const [open, setOpen] = useState(false)
  return (
    <Collapsible
      open={open}
      onOpenChange={setOpen}
      className='flex min-w-0 flex-col rounded-lg border border-dashed bg-muted/20'
    >
      <div className='flex min-w-0 flex-wrap items-center gap-3 p-3'>
        <Medallion icon={SlidersHorizontal} tone='muted' size='sm' />
        <div className='flex min-w-0 flex-1 basis-48 flex-col gap-0.5'>
          <Text weight='semibold'>{title}</Text>
          <Muted variant='caption'>{note}</Muted>
        </div>
        <CollapsibleTrigger asChild>
          <Button size='sm' variant={open ? 'secondary' : 'outline'}>
            <SlidersHorizontal />
            {open ? 'Close the controls' : 'Adjust'}
            <ChevronDown
              className={cn('transition-transform', open && 'rotate-180')}
            />
          </Button>
        </CollapsibleTrigger>
      </div>
      <CollapsibleContent className='@container flex min-w-0 flex-col gap-5 border-t border-dashed p-3'>
        {children}
      </CollapsibleContent>
    </Collapsible>
  )
}

export function EditorGroup({
  title,
  icon: Icon,
  pairs = false,
  children,
}: {
  title: string
  icon: LucideIcon
  pairs?: boolean
  children: ReactNode
}) {
  return (
    <div className='flex min-w-0 flex-col gap-2.5'>
      <div className='flex min-w-0 items-center gap-1.5'>
        <Icon aria-hidden='true' className='size-icon-xs text-primary' />
        <Label variant='overline'>{title}</Label>
      </div>
      <div
        className={cn(
          'grid min-w-0 grid-cols-1 gap-3 @md:grid-cols-2',
          !pairs && '@xl:grid-cols-3'
        )}
      >
        {children}
      </div>
    </div>
  )
}

export function EditorTile({
  icon,
  tone,
  label,
  htmlFor,
  hint,
  held,
  control,
  children,
}: {
  icon: LucideIcon
  tone: KpiTone
  label: string
  htmlFor?: string
  hint: string
  held: boolean
  control?: ReactNode
  children?: ReactNode
}) {
  return (
    <div className='flex h-full min-w-0 flex-col justify-between gap-2.5 rounded-lg border bg-card p-3'>
      <div className='flex min-w-0 items-center gap-2.5'>
        <Medallion icon={icon} tone={tone} size='sm' />
        <div className='flex min-w-0 flex-1 flex-col'>
          <FieldLabel htmlFor={htmlFor} className='truncate'>
            {label}
          </FieldLabel>
          <Muted as='span' variant='caption' truncate={2}>
            {hint}
          </Muted>
        </div>
        {held && (
          <Badge size='sm' variant='default'>
            <Lock />
            Held
          </Badge>
        )}
        {control}
      </div>
      {children}
    </div>
  )
}

const OPEN_ENDED = 1000000

export type NumberField = {
  key: string
  label: string
  icon: LucideIcon
  value: number
  min: number
  max: number
  unit?: string
}

function problem(field: NumberField, parsed: number | null): string | null {
  if (parsed === null || !Number.isInteger(parsed))
    return 'Give a whole number.'
  if (parsed < field.min || parsed > field.max)
    return field.max >= OPEN_ENDED
      ? `Must be ${field.min} or more.`
      : `Must be ${field.min}–${field.max}.`
  if (parsed === field.value) return 'This is the present value.'
  return null
}

export function NumberEditor({
  id,
  field,
  held,
  blocked,
  pending,
  onSet,
}: {
  id: string
  field: NumberField
  held: boolean
  blocked: string | null
  pending: boolean
  onSet: (value: number) => void
}) {
  const [draft, setDraft] = useState(String(field.value))
  const parsed = draft.trim() === '' ? null : Number(draft)
  const reason = blocked ?? problem(field, parsed) ?? (pending ? WORKING : null)
  const inputId = `${id}-${field.key}`
  return (
    <form
      className='min-w-0'
      onSubmit={(event) => {
        event.preventDefault()
        if (reason === null && parsed !== null) onSet(parsed)
      }}
    >
      <EditorTile
        icon={field.icon}
        tone={held ? 'gold' : 'muted'}
        label={field.label}
        htmlFor={inputId}
        hint={`${field.max >= OPEN_ENDED ? `${field.min} or more` : `${field.min}–${field.max}`}${field.unit ? ` ${field.unit}` : ''}`}
        held={held}
      >
        <div className='flex min-w-0 items-center gap-2'>
          <Input
            id={inputId}
            type='number'
            inputMode='numeric'
            min={field.min}
            max={field.max}
            value={draft}
            disabled={blocked !== null}
            onChange={(event) => setDraft(event.target.value)}
          />
          <Button
            type='submit'
            variant='outline'
            size='icon'
            aria-label={`Set ${field.label}`}
            disabled={reason !== null}
            disabledReason={reason ?? undefined}
          >
            <Check />
          </Button>
        </div>
      </EditorTile>
    </form>
  )
}

export function ChoiceEditor({
  label,
  value,
  table,
  held,
  blocked,
  hint,
  onPick,
}: {
  label: string
  value: string
  table: Record<string, Spec>
  held: boolean
  blocked: string | null
  hint: string
  onPick: (value: string) => void
}) {
  const current = table[value]
  return (
    <EditorTile
      icon={current?.icon ?? SlidersHorizontal}
      tone={current?.tone ?? 'muted'}
      label={label}
      hint={hint}
      held={held}
    >
      <Select value={value} onValueChange={onPick} disabled={blocked !== null}>
        <SelectTrigger aria-label={label} className='w-full'>
          <SelectValue />
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
    </EditorTile>
  )
}

export function IconPicker({
  label,
  value,
  table,
  blocked,
  onPick,
}: {
  label: string
  value: string
  table: Record<string, Spec>
  blocked: string | null
  onPick: (value: string) => void
}) {
  const id = useId()
  return (
    <div className='flex min-w-0 flex-col gap-1.5'>
      <FieldLabel htmlFor={id}>{label}</FieldLabel>
      <Select value={value} onValueChange={onPick} disabled={blocked !== null}>
        <SelectTrigger id={id} aria-label={label} className='w-full'>
          <SelectValue />
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
    </div>
  )
}

export function FlagEditor({
  label,
  hint,
  icon,
  tone,
  checked,
  held,
  blocked,
  onToggle,
}: {
  label: string
  hint: string
  icon: LucideIcon
  tone: KpiTone
  checked: boolean
  held: boolean
  blocked: string | null
  onToggle: (value: boolean) => void
}) {
  return (
    <EditorTile
      icon={icon}
      tone={checked ? tone : 'muted'}
      label={label}
      hint={hint}
      held={held}
      control={
        <Switch
          checked={checked}
          disabled={blocked !== null}
          onCheckedChange={onToggle}
          aria-label={label}
        />
      }
    />
  )
}

export function HeldStrip({
  keys,
  labelOf,
  blocked,
  onRelease,
}: {
  keys: string[]
  labelOf: (key: string) => string
  blocked: string | null
  onRelease: (keys: string[]) => void
}) {
  if (keys.length === 0)
    return (
      <div className='flex min-w-0 items-center gap-2'>
        <Unlock
          aria-hidden='true'
          className='size-icon-xs text-muted-foreground'
        />
        <Muted variant='caption'>
          Nothing is held; every value follows the world.
        </Muted>
      </div>
    )
  return (
    <div className='flex min-w-0 flex-col gap-2 rounded-lg border border-primary/30 bg-primary/5 p-3'>
      <div className='flex min-w-0 items-center gap-2'>
        <Lock aria-hidden='true' className='size-icon-xs text-primary' />
        <Text as='span' weight='medium'>
          {`${keys.length} held against the world`}
        </Text>
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        {keys.map((key) => (
          <Button
            key={key}
            size='sm'
            variant='outline'
            disabled={blocked !== null}
            disabledReason={blocked ?? undefined}
            onClick={() => onRelease([key])}
          >
            <Unlock />
            {`Release ${labelOf(key).toLowerCase()}`}
          </Button>
        ))}
        {keys.length > 1 && (
          <Button
            size='sm'
            variant='secondary'
            disabled={blocked !== null}
            disabledReason={blocked ?? undefined}
            onClick={() => onRelease(keys)}
          >
            <Unlock />
            Release them all
          </Button>
        )}
      </div>
    </div>
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
      role='img'
      aria-label={`${label} ${value} of ${max}`}
      className='inline-flex shrink-0 items-center gap-0.5'
    >
      {Array.from({ length: max }, (_, index) => (
        <span
          key={index}
          className={cn(
            'h-meter-md w-2.5 rounded-full border',
            index < value && PIP_TONE[tone]
          )}
        />
      ))}
    </span>
  )
}

import { type ReactNode } from 'react'
import { type LucideIcon } from 'lucide-react'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Medallion } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'

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
          ? 'flex min-w-0 flex-col gap-3 rounded-lg border bg-background p-3 @xl/mind:col-span-2'
          : 'flex min-w-0 flex-col gap-3 rounded-lg border bg-background p-3'
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
}: {
  label: string
  value: string
  table: Record<string, string>
  blocked: string | null
  placeholder?: string
  onPick: (value: string) => void
}) {
  return (
    <div className='flex min-w-0 flex-col gap-1'>
      <Label>{label}</Label>
      <Select value={value} onValueChange={onPick} disabled={blocked !== null}>
        <SelectTrigger aria-label={label}>
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
    </div>
  )
}

export function ControlPanel({
  title,
  note,
  hold,
  onHold,
  children,
}: {
  title: string
  note: string
  hold?: boolean
  onHold?: (value: boolean) => void
  children: ReactNode
}) {
  return (
    <div className='flex min-w-0 flex-col gap-4 rounded-lg border border-dashed bg-muted/20 p-3'>
      <div className='flex min-w-0 flex-wrap items-center justify-between gap-3'>
        <div className='flex min-w-0 flex-col gap-0.5'>
          <Text weight='semibold'>{title}</Text>
          <Muted variant='caption'>{note}</Muted>
        </div>
        {onHold && (
          <label className='flex shrink-0 items-center gap-2'>
            <Switch
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

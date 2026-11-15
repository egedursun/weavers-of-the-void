import { CalendarClock, Trophy } from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { Switch } from '@/components/ui/switch'
import { FormRow, Medallion } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { type GoalQuote } from './api'

export function CountField({
  label,
  description,
  value,
  min,
  max,
  onChange,
}: {
  label: string
  description?: string
  value: string
  min: number
  max: number
  onChange: (value: string) => void
}) {
  return (
    <FormRow label={label} description={description}>
      {(id) => (
        <Input
          id={id}
          type='number'
          inputMode='numeric'
          min={min}
          max={max}
          value={value}
          className='w-32'
          onChange={(event) => onChange(event.target.value)}
        />
      )}
    </FormRow>
  )
}

export function DeadlineField({
  enabled,
  epochs,
  max,
  onEnabled,
  onEpochs,
}: {
  enabled: boolean
  epochs: string
  max: number
  onEnabled: (enabled: boolean) => void
  onEpochs: (value: string) => void
}) {
  return (
    <FormRow
      label='Deadline'
      description='A goal with a deadline is worth more; it fails if the epochs run out first.'
    >
      {(id) => (
        <>
          <Switch
            id={id}
            checked={enabled}
            onCheckedChange={onEnabled}
            aria-label='Set a deadline'
          />
          <Input
            type='number'
            inputMode='numeric'
            min={1}
            max={max}
            value={epochs}
            disabled={!enabled}
            aria-label='Epochs until the deadline'
            className='w-32'
            onChange={(event) => onEpochs(event.target.value)}
          />
          <Muted variant='caption'>
            {enabled ? 'epochs from now' : 'No deadline: the goal waits'}
          </Muted>
        </>
      )}
    </FormRow>
  )
}

export function QuotePreview({
  quote,
  pending,
  deadline,
}: {
  quote: GoalQuote | undefined
  pending: boolean
  deadline: number | null
}) {
  if (!quote)
    return pending ? <Skeleton className='h-control-lg w-full' /> : null
  return (
    <div
      data-goal-quote
      className='flex min-w-0 items-start gap-3 rounded-xl border border-primary/30 bg-primary/5 p-3'
    >
      <Medallion icon={Trophy} />
      <div className='flex min-w-0 flex-1 flex-col gap-1'>
        <Text as='span' weight='semibold'>
          {quote.name}
        </Text>
        <Muted variant='caption'>{quote.description}</Muted>
        <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
          <Badge size='sm'>
            <Trophy />
            {`+${formatInteger(quote.points)}`}
          </Badge>
          <Badge size='sm' variant='outline'>
            {`Target ${formatInteger(quote.target)}`}
          </Badge>
          <Badge size='sm' variant='outline'>
            {`Now ${formatInteger(quote.start_value)}`}
          </Badge>
          {deadline !== null && (
            <Badge size='sm' variant='warning'>
              <CalendarClock />
              {`Within ${plural(deadline, 'epoch', 'epochs')}`}
            </Badge>
          )}
        </div>
      </div>
      <Label>{pending ? 'Weighing…' : 'Worth'}</Label>
    </div>
  )
}

import { Compass } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Label, Muted, Text } from '@/components/typography'
import {
  OUTCOME_LABEL,
  OUTCOME_VARIANT,
  DECLARER_LABEL,
  PERCENT,
  countdownText,
  expeditionProgress,
} from './expeditionFormat'
import { type GreatExpedition } from './expeditionsApi'

export function ExpeditionCard({
  expedition,
}: {
  expedition: GreatExpedition
}) {
  const open = expedition.outcome === null
  return (
    <article
      data-expedition-id={expedition.thread_id}
      className='flex min-w-0 flex-col gap-2 rounded-lg border bg-card p-3'
    >
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Compass
          aria-hidden='true'
          className='size-icon-sm shrink-0 text-primary'
        />
        <Text as='span' weight='medium' truncate className='min-w-0 flex-1'>
          {expedition.name}
        </Text>
        <Badge
          size='sm'
          variant={
            expedition.outcome ? OUTCOME_VARIANT[expedition.outcome] : 'default'
          }
        >
          {expedition.outcome ? OUTCOME_LABEL[expedition.outcome] : 'Under way'}
        </Badge>
        <Badge
          size='sm'
          variant={
            expedition.thread_status === 'open' ? 'outline' : 'secondary'
          }
        >
          {expedition.thread_status === 'open' ? 'Story open' : 'Story closed'}
        </Badge>
      </div>
      <Muted variant='caption'>{expedition.text}</Muted>
      <div className='flex min-w-0 flex-wrap gap-1.5'>
        <Badge
          size='sm'
          variant='outline'
        >{`Declared by ${DECLARER_LABEL[expedition.declared_by]}`}</Badge>
        <Badge
          size='sm'
          variant='outline'
        >{`Opened in epoch ${expedition.opened_epoch}`}</Badge>
        <Badge
          size='sm'
          variant='outline'
        >{`Deadline: epoch ${expedition.deadline_epoch}`}</Badge>
      </div>
      <Progress
        value={expeditionProgress(expedition) * PERCENT}
        size='sm'
        tone={
          open
            ? expedition.epochs_remaining <= 1
              ? 'warning'
              : 'default'
            : expedition.outcome === 'completed'
              ? 'success'
              : 'muted'
        }
        aria-label='Time until the deadline'
      />
      <Label>{countdownText(expedition)}</Label>
    </article>
  )
}

export function ExpeditionNote({
  expedition,
}: {
  expedition: GreatExpedition
}) {
  return (
    <div
      data-expedition-note={expedition.thread_id}
      className='flex min-w-0 flex-col gap-2'
    >
      <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
        <Badge size='sm' variant='default'>
          <Compass aria-hidden='true' />
          {expedition.name}
        </Badge>
        <Badge
          size='sm'
          variant={
            expedition.outcome ? OUTCOME_VARIANT[expedition.outcome] : 'outline'
          }
        >
          {countdownText(expedition)}
        </Badge>
        <Badge
          size='sm'
          variant='outline'
        >{`Opened ${expedition.opened_epoch} · deadline ${expedition.deadline_epoch}`}</Badge>
      </div>
      <Progress
        value={expeditionProgress(expedition) * PERCENT}
        size='sm'
        tone={
          expedition.outcome === null
            ? 'default'
            : expedition.outcome === 'completed'
              ? 'success'
              : 'muted'
        }
        aria-label='Time until the deadline'
      />
    </div>
  )
}

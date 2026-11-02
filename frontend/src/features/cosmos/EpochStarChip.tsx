import { SunMoon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { Skeleton } from '@/components/ui/skeleton'
import { EntityLink, ExpandableText, PagedList } from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import { RulingSkyList } from './RulingSkyList'
import { useEpochStar } from './expeditionsApi'

const HISTORY_SHOWN = 8

export function EpochStarChip() {
  const view = useEpochStar()
  if (view.isError) return null
  if (view.isPending) return <Skeleton className='h-badge-md w-32' />
  const crowned = view.data.current.filter((item) => item.star !== null)
  const lead = crowned.length === 1 ? crowned[0] : null
  const text = lead?.star
    ? lead.star.name
    : crowned.length > 1
      ? `Ruling skies · ${crowned.length} worlds`
      : 'No ruling sky yet'
  const label = `Ruling sky of the epoch: ${text}`
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          variant={crowned.length > 0 ? 'secondary' : 'outline'}
          size='sm'
          aria-label={label}
          data-epoch-star
        >
          <SunMoon />
          <span className='min-w-0 truncate'>{text}</span>
        </Button>
      </PopoverTrigger>
      <PopoverContent
        align='start'
        className='flex max-h-96 w-80 max-w-full flex-col gap-3 overflow-y-auto'
      >
        <Label>Ruling skies of the epoch</Label>
        {view.data.current.length === 0 ? (
          <Muted>No world has a ruling sky yet.</Muted>
        ) : (
          <RulingSkyList entries={view.data.current} />
        )}
        <Label>History</Label>
        {view.data.history.length === 0 ? (
          <Muted>No epoch has crowned a ruling sky yet.</Muted>
        ) : (
          <PagedList
            items={view.data.history}
            initial={HISTORY_SHOWN}
            noun={['epoch', 'epochs']}
            className='flex min-w-0 flex-col gap-2'
            itemKey={(entry) => entry.epoch}
          >
            {(entry) => (
              <li className='flex min-w-0 flex-col gap-0.5'>
                <div className='flex min-w-0 flex-wrap items-baseline gap-x-2'>
                  <Muted
                    as='span'
                    variant='caption'
                  >{`Epoch ${entry.epoch}`}</Muted>
                  {entry.entity_id !== null && entry.name !== null && (
                    <EntityLink kind='entity' id={String(entry.entity_id)}>
                      {entry.name}
                    </EntityLink>
                  )}
                </div>
                <ExpandableText variant='caption' lines={2}>
                  {entry.text}
                </ExpandableText>
              </li>
            )}
          </PagedList>
        )}
      </PopoverContent>
    </Popover>
  )
}

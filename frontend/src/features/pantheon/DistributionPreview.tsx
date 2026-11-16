import { ArrowRightLeft, Globe, ShieldCheck } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import {
  EntityLink,
  Medallion,
  Paged,
  PagedList,
  Portrait,
} from '@/components/domain'
import { Label, Muted, Stat, Text } from '@/components/typography'
import { type WorldBrief, useDistributionPreview, useSons } from './api'
import { mediaUrl } from './media'

const SHOWN_CANDIDATES = 6

export function DistributionPreviewPanel({ worlds }: { worlds: WorldBrief[] }) {
  const preview = useDistributionPreview()
  const sons = useSons()
  const worldName = (worldId: number | null) =>
    worlds.find((world) => world.id === worldId)?.name ?? 'no world'
  const sonView = (sonId: number) =>
    (sons.data ?? []).find((view) => view.son.id === sonId)
  if (preview.isPending) return <Skeleton className='h-control-lg w-full' />
  if (preview.isError)
    return <Text tone='destructive'>{preview.error.message}</Text>
  const {
    candidates,
    next_son_id: nextId,
    godless_world_ids: godless,
  } = preview.data
  const next = candidates.find((item) => item.son_id === nextId)
  return (
    <div className='flex min-w-0 flex-col gap-4 rounded-md border surface-framed border-gild/70 bg-card p-3'>
      <div className='grid min-w-0 grid-cols-1 gap-3 md:grid-cols-2'>
        <div className='flex min-w-0 items-center gap-3'>
          <Medallion
            icon={Globe}
            tone={godless.length > 0 ? 'warning' : 'success'}
          />
          <div className='flex min-w-0 flex-1 flex-col gap-1'>
            <Label variant='overline'>Godless worlds</Label>
            {godless.length === 0 ? (
              <Muted variant='caption'>
                Every world has a son; no one moves.
              </Muted>
            ) : (
              <PagedList
                items={godless}
                initial={12}
                noun={['entry', 'entries']}
                as='div'
                className='flex min-w-0 flex-wrap gap-1.5'
                itemKey={(id) => id}
              >
                {(id) => (
                  <Badge key={id} size='sm' variant='warning'>
                    {worldName(id)}
                  </Badge>
                )}
              </PagedList>
            )}
          </div>
        </div>
        <div className='flex min-w-0 items-center gap-3'>
          <Medallion icon={ArrowRightLeft} tone={next ? 'gold' : 'muted'} />
          <div className='flex min-w-0 flex-1 flex-col gap-1'>
            <Label variant='overline'>Next to move</Label>
            {next ? (
              <Text truncate>
                <EntityLink kind='son' id={String(next.son_id)}>
                  {next.name}
                </EntityLink>
                {`, now in ${worldName(next.world_id)}`}
              </Text>
            ) : (
              <Muted variant='caption'>No son can be moved right now.</Muted>
            )}
          </div>
        </div>
      </div>
      {candidates.length > 0 && (
        <div className='flex min-w-0 flex-col gap-2'>
          <Label variant='overline'>Who moves first</Label>
          <ol className='grid min-w-0 grid-cols-1 gap-1.5 lg:grid-cols-2 2xl:grid-cols-3'>
            <Paged items={candidates.slice(0, SHOWN_CANDIDATES)} as='li'>
              {(item, position) => {
                const view = sonView(item.son_id)
                const first = item.son_id === nextId
                return (
                  <li
                    key={item.son_id}
                    className={cn(
                      'flex min-w-0 items-center gap-3 rounded-md border surface-sheen border-gild/60 bg-card p-2',
                      first ? 'border-primary/40 bg-primary/5' : 'bg-card'
                    )}
                  >
                    <span
                      className={cn(
                        'flex size-control-sm shrink-0 items-center justify-center rounded-full border surface-sheen border-gild/60 bg-card',
                        first
                          ? 'border-primary/40 bg-primary/12 text-primary'
                          : 'border-border bg-muted text-muted-foreground'
                      )}
                    >
                      <Stat value={position + 1} />
                    </span>
                    <Portrait
                      name={item.name}
                      src={mediaUrl(view?.cover)}
                      size='sm'
                      rarity={view?.son.rarity}
                    />
                    <span className='flex min-w-0 flex-1 flex-col'>
                      <EntityLink
                        kind='son'
                        id={String(item.son_id)}
                        rarity={view?.son.rarity}
                      >
                        {item.name}
                      </EntityLink>
                      <Muted variant='caption' truncate>
                        {worldName(item.world_id)}
                      </Muted>
                    </span>
                    {item.protected && (
                      <Badge size='sm' variant='info'>
                        <ShieldCheck />
                        Spared
                      </Badge>
                    )}
                    <Badge size='sm' variant='outline'>
                      {`Score ${item.score}`}
                    </Badge>
                  </li>
                )
              }}
            </Paged>
          </ol>
          {candidates.length > SHOWN_CANDIDATES && (
            <Muted variant='caption'>{`${candidates.length - SHOWN_CANDIDATES} more wait behind them.`}</Muted>
          )}
        </div>
      )}
    </div>
  )
}

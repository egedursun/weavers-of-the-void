import { ChevronsUpDown, History } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Skeleton } from '@/components/ui/skeleton'
import {
  EmptyState,
  ExpandableText,
  Section,
  ShowMore,
  useShowMore,
} from '@/components/domain'
import { Text } from '@/components/typography'
import { ChronicleList } from '@/features/pantheon/ChronicleList'
import { humanize } from '@/features/pantheon/labels'
import { type SonDetail, useSonLedger } from './api'

type LedgerEntries = NonNullable<
  ReturnType<typeof useSonLedger>['data']
>['entries']

const EPOCHS_SHOWN = 4
const ACTIONS_SHOWN = 8

function TurnEpoch({
  epoch,
  list,
  open,
}: {
  epoch: number
  list: LedgerEntries
  open: boolean
}) {
  const page = useShowMore(list, ACTIONS_SHOWN)
  const changes = list.reduce((sum, view) => sum + view.change_count, 0)
  return (
    <Collapsible
      defaultOpen={open}
      className='flex min-w-0 flex-col gap-2 rounded-lg border bg-card p-3'
    >
      <CollapsibleTrigger asChild>
        <Button variant='ghost' size='sm' className='self-start'>
          <ChevronsUpDown />
          {`Epoch ${epoch} · ${list.length} actions · ${changes} changes`}
        </Button>
      </CollapsibleTrigger>
      <CollapsibleContent className='flex min-w-0 flex-col gap-3'>
        <ol className='flex min-w-0 flex-col gap-2'>
          {page.visible.map((view) => (
            <li
              key={view.entry.id}
              className={cn(
                'flex min-w-0 flex-col gap-0.5 border-l-2 border-primary/30 pl-3',
                view.entry.undone && 'opacity-60'
              )}
            >
              <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
                <Text as='span' weight='medium' title={view.entry.tool}>
                  {view.label || humanize(view.entry.tool)}
                </Text>
                {view.entry.undone && (
                  <Badge size='sm' variant='secondary'>
                    Undone
                  </Badge>
                )}
              </div>
              {view.entry.input_summary && (
                <ExpandableText variant='caption' tone='muted' lines={2}>
                  {view.entry.input_summary}
                </ExpandableText>
              )}
              {view.rows.length > 0 && (
                <ExpandableText variant='caption' lines={2}>
                  {view.rows.join(' · ')}
                </ExpandableText>
              )}
            </li>
          ))}
        </ol>
        <ShowMore state={page} noun={['action', 'actions']} />
      </CollapsibleContent>
    </Collapsible>
  )
}

function TurnEpochs({
  epochs,
  byEpoch,
}: {
  epochs: number[]
  byEpoch: Map<number, LedgerEntries>
}) {
  const page = useShowMore(epochs, EPOCHS_SHOWN)
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      {page.visible.map((epoch, index) => (
        <TurnEpoch
          key={epoch}
          epoch={epoch}
          list={byEpoch.get(epoch) ?? []}
          open={index === 0}
        />
      ))}
      <ShowMore state={page} noun={['epoch', 'epochs']} />
    </div>
  )
}

export function SonTurns({
  sonId,
  chronicle,
}: {
  sonId: number
  chronicle: SonDetail['chronicle']
}) {
  const ledger = useSonLedger(sonId)
  const entries = ledger.data?.entries ?? []
  const byEpoch = new Map<number, typeof entries>()
  for (const view of entries) {
    const list = byEpoch.get(view.entry.epoch) ?? []
    list.push(view)
    byEpoch.set(view.entry.epoch, list)
  }
  const epochs = [...byEpoch.keys()].sort((a, b) => b - a)
  return (
    <>
      <Section
        title='Turns'
        description='What he did each epoch, from the action ledger.'
        level={3}
      >
        {ledger.isPending ? (
          <Skeleton className='h-textarea w-full' />
        ) : ledger.isError ? (
          <Text tone='destructive'>{ledger.error.message}</Text>
        ) : epochs.length === 0 ? (
          <EmptyState
            icon={History}
            size='compact'
            title='No turn in the ledger'
            description='His actions are recorded here once he takes a turn.'
          />
        ) : (
          <TurnEpochs epochs={epochs} byEpoch={byEpoch} />
        )}
      </Section>
      <ChronicleList
        title='Trace in the chronicle'
        lines={chronicle}
        emptyTitle='None yet'
        emptyText='Chronicle lines about him appear here.'
      />
    </>
  )
}

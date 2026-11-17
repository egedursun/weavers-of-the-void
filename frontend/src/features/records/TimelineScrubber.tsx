import { useState } from 'react'
import { ArrowRight, Hourglass } from 'lucide-react'
import {
  EmptyState,
  EpochSlider,
  LoadingBlock,
  ShowMore,
  useShowMore,
} from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { RecordRow } from '@/features/cosmography/parts'
import { useWorldState } from '@/features/entity/api/queries'
import { type StateAtRow, useStateAt } from './api'
import { spokenKey } from './format'

const ROWS = 40
const SHOWN = 6

function rowCaption(row: StateAtRow): string {
  if (!row.existed) return 'It did not exist yet'
  if (!row.exists_now) return 'It is gone now'
  const changed = row.fields.filter((field) => field.changed).length
  return changed
    ? `${changed} ${changed === 1 ? 'value differs' : 'values differ'} from now`
    : 'As it is now'
}

export function ThenAndNow({
  rows,
  empty,
}: {
  rows: readonly StateAtRow[]
  empty: string
}) {
  const changed = rows.filter(
    (row) =>
      !row.existed ||
      !row.exists_now ||
      row.fields.some((field) => field.changed)
  )
  const shown = useShowMore(changed, SHOWN)
  if (!changed.length) return <Muted>{empty}</Muted>
  return (
    <>
      <ul className='flex min-w-0 flex-col gap-2'>
        {shown.visible.map((row) => (
          <RecordRow
            key={`${row.table_name}-${row.row_key}`}
            icon={Hourglass}
            tone='info'
            title={spokenKey(row.table_name)}
            caption={rowCaption(row)}
          >
            <dl className='grid min-w-0 grid-cols-1 gap-1'>
              {row.fields
                .filter((field) => field.changed)
                .map((field) => (
                  <div
                    key={field.field}
                    className='flex min-w-0 flex-wrap items-baseline gap-1 border-b border-dashed pb-1'
                  >
                    <dt className='shrink-0'>
                      <Muted as='span' variant='caption'>
                        {spokenKey(field.field)}
                      </Muted>
                    </dt>
                    <dd className='flex min-w-0 flex-wrap items-baseline gap-1'>
                      <Text as='span'>{field.then ?? 'Nothing'}</Text>
                      <ArrowRight
                        aria-hidden='true'
                        className='size-icon-xs text-muted-foreground'
                      />
                      <Text as='span' weight='semibold'>
                        {field.now ?? 'Nothing'}
                      </Text>
                    </dd>
                  </div>
                ))}
            </dl>
          </RecordRow>
        ))}
      </ul>
      <ShowMore state={shown} noun={['record', 'records']} />
    </>
  )
}

export function TimelineScrubber({ nodeId }: { nodeId: number }) {
  const state = useWorldState()
  const present = state.data?.world?.epoch ?? 1
  const [epoch, setEpoch] = useState<number | null>(null)
  const chosen = epoch ?? present
  const then = useStateAt(
    chosen < present
      ? { epoch: chosen, nodeId, table: null, limit: ROWS }
      : null
  )
  return (
    <div
      data-surface='TimelineScrubber'
      className='flex min-w-0 flex-col gap-2 rounded-md border surface-framed border-gild/70 bg-card p-3'
    >
      <EpochSlider
        label='Then and now'
        value={chosen}
        max={present}
        disabled={present <= 1}
        valueLabel={chosen === present ? 'Now' : `Epoch ${chosen}`}
        onChange={setEpoch}
      />
      {present <= 1 ? (
        <Muted variant='caption'>
          The world has lived only its first epoch; there is no earlier moment
          to look back to.
        </Muted>
      ) : chosen === present ? (
        <Muted variant='caption'>
          Move back to see it as it was at the start of an earlier epoch.
        </Muted>
      ) : then.isPending ? (
        <LoadingBlock label='Reading it as it was' />
      ) : then.isError ? (
        <EmptyState
          icon={Hourglass}
          size='inline'
          title='It could not be read as it was'
          description={then.error.message}
        />
      ) : (
        <ThenAndNow
          rows={then.data.rows}
          empty={`It was as it is now at the start of epoch ${chosen}.`}
        />
      )}
    </div>
  )
}

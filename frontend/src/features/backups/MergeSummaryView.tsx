import { type KeyValueItem, KeyValueList, Paged } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { type MergeSummary } from './api'

const NOT_CARRIED = [
  'Sons and the creator',
  'The ledger, jobs and notifications',
  'Epoch history, statistics and engine bookkeeping',
  'Messages, councils and achievements',
  'World rule overrides and the name registry',
]

const CARRIED = [
  'Entities, worlds and places',
  'Bonds, beliefs and chronicle lines',
  'Images, with new file names when they collide',
]

function countItems(counts: Record<string, number>): KeyValueItem[] {
  return Object.entries(counts)
    .filter(([, count]) => count > 0)
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([table, count]) => ({
      key: table,
      label: table.replaceAll('_', ' '),
      value: count.toLocaleString('en-US'),
    }))
}

function Group({
  title,
  children,
}: {
  title: string
  children: React.ReactNode
}) {
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <Label>{title}</Label>
      {children}
    </div>
  )
}

export function MergeExplanation() {
  return (
    <div className='grid min-w-0 gap-4 md:grid-cols-2'>
      <Group title='Carried into your world'>
        <ul className='flex min-w-0 flex-col gap-1'>
          {CARRIED.map((line) => (
            <Text as='li' key={line} variant='caption'>
              {line}
            </Text>
          ))}
        </ul>
      </Group>
      <Group title='Not carried'>
        <ul className='flex min-w-0 flex-col gap-1'>
          {NOT_CARRIED.map((line) => (
            <Text as='li' key={line} variant='caption'>
              {line}
            </Text>
          ))}
        </ul>
      </Group>
    </div>
  )
}

export function MergeSummaryView({ summary }: { summary: MergeSummary }) {
  const rows = countItems(summary.rows)
  const skipped = countItems(summary.skipped)
  const images = Object.entries(summary.images)
  return (
    <div className='flex min-w-0 flex-col gap-4' data-testid='merge-summary'>
      <Group title='Rows added per table'>
        {rows.length > 0 ? (
          <KeyValueList items={rows} />
        ) : (
          <Muted>Nothing was added.</Muted>
        )}
      </Group>
      {skipped.length > 0 && (
        <Group title='Rows skipped'>
          <KeyValueList items={skipped} />
        </Group>
      )}
      {summary.renamed.length > 0 && (
        <Group title='Renamed to avoid clashes'>
          <ul className='flex min-w-0 flex-col gap-1'>
            <Paged items={summary.renamed} as='li'>
              {(node) => (
                <Text
                  as='li'
                  key={`${node.old_name}-${node.new_name}`}
                  truncate
                >
                  {`${node.old_name} became ${node.new_name}`}
                </Text>
              )}
            </Paged>
          </ul>
        </Group>
      )}
      {images.length > 0 && (
        <Group title='Images renamed'>
          <ul className='flex min-w-0 flex-col gap-1'>
            <Paged items={images} as='li'>
              {([from, to]) => (
                <Text as='li' key={from} variant='caption' truncate>
                  {`${from} became ${to}`}
                </Text>
              )}
            </Paged>
          </ul>
        </Group>
      )}
    </div>
  )
}

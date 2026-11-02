import {
  Activity,
  BookOpenText,
  Crown,
  Eye,
  Globe,
  Link2,
  type LucideIcon,
  Orbit,
  RotateCcw,
  ScrollText,
  Trash2,
  Users,
} from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import {
  EmptyState,
  type KpiTone,
  Medallion,
  Section,
} from '@/components/domain'
import { Label, Stat, Text } from '@/components/typography'
import { type ChangeTally, EMPTY_TALLY, useChangeDigest } from './api'

type DigestRow = {
  label: string
  value: number | null
  icon: LucideIcon
  tone: KpiTone
}

function rowsOf(tally: ChangeTally): DigestRow[] {
  const counts: DigestRow[] = [
    {
      label: 'Records changed',
      value: tally.entities,
      icon: ScrollText,
      tone: 'verdigris',
    },
    {
      label: 'Records removed',
      value: tally.removedEntities,
      icon: Trash2,
      tone: 'danger',
    },
    { label: 'Sons changed', value: tally.sons, icon: Crown, tone: 'info' },
    {
      label: 'New chronicle lines',
      value: tally.chronicleLines,
      icon: BookOpenText,
      tone: 'gold',
    },
    {
      label: 'Foreign gods changed',
      value: tally.foreignGods,
      icon: Eye,
      tone: 'warning',
    },
  ]
  const flags: DigestRow[] = [
    {
      label: 'Bonds changed',
      value: tally.bonds ? null : 0,
      icon: Link2,
      tone: 'verdigris',
    },
    {
      label: 'Cosmos changed',
      value: tally.cosmos ? null : 0,
      icon: Orbit,
      tone: 'info',
    },
    {
      label: 'Worlds changed',
      value: tally.worlds ? null : 0,
      icon: Globe,
      tone: 'info',
    },
    {
      label: 'Son relations changed',
      value: tally.relations ? null : 0,
      icon: Users,
      tone: 'gold',
    },
  ]
  return [...counts, ...flags].filter((row) => row.value !== 0)
}

function DigestTile({ row }: { row: DigestRow }) {
  return (
    <li className='flex min-w-0 items-center gap-3 rounded-lg border bg-background p-3'>
      <Medallion icon={row.icon} tone={row.tone} size='sm' />
      <Label truncate title={row.label} className='flex-1'>
        {row.label}
      </Label>
      {row.value === null ? (
        <Badge variant='info' className='shrink-0'>
          Changed
        </Badge>
      ) : (
        <Stat value={formatInteger(row.value)} className='shrink-0' />
      )}
    </li>
  )
}

export function ChangeDigestPanel() {
  const { query, tally, reset } = useChangeDigest()
  const rows = rowsOf(tally)
  const quiet = rows.length === 0 && !tally.rebuilt
  return (
    <Section
      title='Changes since you arrived'
      description='The world digest, updated as the world changes.'
      surface='card'
      level={3}
      stretch
      actions={
        <Button
          variant='outline'
          size='sm'
          disabled={tally === EMPTY_TALLY}
          disabledReason='Nothing has changed yet.'
          onClick={reset}
        >
          <RotateCcw />
          Clear
        </Button>
      }
    >
      {query.isPending && <Skeleton className='h-24 w-full' />}
      {query.isError && <Text tone='destructive'>{query.error.message}</Text>}
      {query.data && tally.rebuilt && (
        <Text tone='warning'>
          The world was rebuilt while you watched; reload to see all of it.
        </Text>
      )}
      {query.data && quiet && (
        <div className='flex min-h-0 flex-1 flex-col *:flex-1'>
          <EmptyState
            size='compact'
            icon={Activity}
            title='Quiet so far'
            description='Changes appear here as the world moves.'
          />
        </div>
      )}
      {rows.length > 0 && (
        <div className='@container/digest min-w-0'>
          <ul className='grid min-w-0 grid-cols-1 gap-2 @md/digest:grid-cols-2'>
            {rows.map((row) => (
              <DigestTile key={row.label} row={row} />
            ))}
          </ul>
        </div>
      )}
    </Section>
  )
}

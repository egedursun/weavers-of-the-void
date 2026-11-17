import { useState } from 'react'
import { CalendarDays, ChevronDown, Flame, ScrollText } from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Skeleton } from '@/components/ui/skeleton'
import { ChangeChip, PagedList } from '@/components/domain'
import { Label, Muted, SectionTitle, Stat, Text } from '@/components/typography'
import {
  HARMFUL_STATS,
  type NumericStat,
  STAT_ICON,
} from '@/features/overview/statFields'
import { EpochNarrative } from './EpochNarrative'
import { FeedLines } from './FeedGroups'
import { YearStrip } from './YearStrip'
import {
  type EpochListItem,
  type EpochStatistics,
  type PerspectiveLine,
  useEpochLines,
} from './api'
import { type LineFilter, filterLines } from './lineFilter'
import { DELTA_FIELDS, deltaOf } from './statDelta'

type EpochArticleProps = {
  epoch: number
  item: EpochListItem | undefined
  ongoing: boolean
  lineCount: number
  stats: EpochStatistics | undefined
  previous: EpochStatistics | undefined
  perspectives: PerspectiveLine[]
  filter: LineFilter
  forceOpen: boolean
  highlightLine: number | null
  kindLabels: Map<string, string>
}

export function EpochArticle({
  epoch,
  item,
  ongoing,
  lineCount,
  stats,
  previous,
  perspectives,
  filter,
  forceOpen,
  highlightLine,
  kindLabels,
}: EpochArticleProps) {
  const [opened, setOpened] = useState(ongoing)
  const open = opened || forceOpen
  const lines = useEpochLines(epoch, open)
  const [year, setYear] = useState<number | null>(null)
  const filtered = filterLines(lines.data?.items ?? [], filter)
  const shown =
    year === null ? filtered : filtered.filter((line) => line.year === year)
  const years =
    item?.year_start !== null && item?.year_start !== undefined
      ? `Years ${formatInteger(item.year_start)}–${item.year_end !== null ? formatInteger(item.year_end) : '…'}`
      : null
  const deltas =
    stats && previous
      ? DELTA_FIELDS.map((field) => deltaOf(field, stats, previous)).filter(
          (delta) => delta.value !== 0
        )
      : []
  return (
    <article
      id={`epoch-${epoch}`}
      data-epoch-article={epoch}
      className={cn(
        'flex min-w-0 scroll-mt-16 flex-col gap-4 rounded-md border surface-framed border-gild/70 bg-card p-4 text-card-foreground md:p-5',
        ongoing && 'border-primary/40'
      )}
    >
      <header className='flex min-w-0 items-start gap-4'>
        <span
          className={cn(
            'medallion size-control-lg font-display',
            ongoing ? 'gem-gold' : 'gem-muted'
          )}
        >
          <Stat value={epoch} />
        </span>
        <div className='flex min-w-0 flex-1 flex-col gap-1.5'>
          <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
            <Label variant='overline'>{`Epoch ${formatInteger(epoch)}`}</Label>
            {ongoing && (
              <Badge size='sm'>
                <Flame />
                Unfolding now
              </Badge>
            )}
            {years && (
              <Badge size='sm' variant='outline'>
                <CalendarDays />
                {years}
              </Badge>
            )}
          </div>
          <SectionTitle truncate={2}>
            {item?.name ??
              (ongoing ? 'The epoch now unfolding' : `Epoch ${epoch}`)}
          </SectionTitle>
          {item?.summary && <Muted>{item.summary}</Muted>}
        </div>
      </header>
      {deltas.length > 0 && (
        <PagedList
          items={deltas}
          initial={12}
          noun={['entry', 'entries']}
          as='ul'
          className='flex min-w-0 flex-wrap gap-1.5'
          listProps={{ 'aria-label': 'Changes since the epoch before' }}
          itemKey={(delta) => delta.field}
        >
          {(delta) => (
            <li key={delta.field}>
              <ChangeChip
                value={delta.value}
                label={delta.label}
                icon={STAT_ICON[delta.field as NumericStat]}
                harmful={HARMFUL_STATS.has(delta.field as NumericStat)}
              />
            </li>
          )}
        </PagedList>
      )}
      {item && <EpochNarrative epoch={item} perspectives={perspectives} />}
      <Collapsible
        open={open}
        onOpenChange={setOpened}
        className='flex min-w-0 flex-col gap-3'
      >
        <CollapsibleTrigger asChild>
          <Button variant='ghost' size='sm' className='self-start'>
            <ScrollText />
            {`Records of the epoch · ${formatInteger(lineCount)}`}
            <ChevronDown
              className={
                open
                  ? 'rotate-180 transition-transform'
                  : 'transition-transform'
              }
            />
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent className='flex min-w-0 flex-col gap-2'>
          {lines.isPending && <Skeleton className='h-textarea w-full' />}
          {lines.isError && (
            <Text tone='destructive'>{lines.error.message}</Text>
          )}
          {lines.isSuccess && shown.length === 0 && (
            <Muted>
              {lines.data.items.length
                ? 'No record of this epoch matches the filters.'
                : 'Nothing was written in this epoch.'}
            </Muted>
          )}
          <YearStrip lines={filtered} selected={year} onSelect={setYear} />
          {shown.length > 0 && (
            <FeedLines
              lines={shown}
              groups={lines.data?.groups ?? []}
              kindLabels={kindLabels}
              highlightLine={highlightLine}
            />
          )}
        </CollapsibleContent>
      </Collapsible>
    </article>
  )
}

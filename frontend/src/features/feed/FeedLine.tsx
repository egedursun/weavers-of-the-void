import { ChevronsDown, ChevronsUp, CornerDownRight } from 'lucide-react'
import { isRarity } from '@/constants/rarity'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { EntityLink, RarityBadge, TimelineItem } from '@/components/domain'
import { MentionText } from '@/components/domain/MentionText'
import { Label, Muted } from '@/components/typography'
import { ReadingGroupView, StreamLineView } from './FeedStreamLine'
import { FEED_SYMBOL_ICON } from './feedLabels'
import { FEED_CATEGORY_LABEL, type FeedLine, type FeedRow } from './feedModel'

const clock = new Intl.DateTimeFormat('en-US', {
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
})

function stamp(line: FeedLine, repeatedEpoch: boolean): string {
  const time = clock.format(new Date(line.at))
  if (line.epoch === null || repeatedEpoch) return time
  return `Epoch ${line.epoch} · ${time}`
}

function LineLink({ line }: { line: FeedLine }) {
  if (!line.link) return null
  if (line.link.kind === 'creator' || line.link.kind === 'help') return null
  return (
    <EntityLink kind={line.link.kind} id={line.link.id} showIcon>
      {line.link.label}
    </EntityLink>
  )
}

type FeedRowViewProps = {
  row: FeedRow
  last: boolean
  onToggleGroup: (key: string) => void
}

export function FeedRowView({ row, last, onToggleGroup }: FeedRowViewProps) {
  if (row.type === 'continues')
    return (
      <li className='flex min-w-0 items-center gap-2 pb-3'>
        <CornerDownRight
          aria-hidden='true'
          className='size-icon-sm shrink-0 text-muted-foreground'
        />
        <Label truncate>
          {row.line.link ? `${row.line.link.label} continues` : 'Continues'}
        </Label>
      </li>
    )
  if (row.type === 'reading')
    return (
      <ReadingGroupView
        lines={row.lines}
        open={row.open}
        groupKey={row.key}
        last={last}
        stamp={stamp(row.lines[0], false)}
        onToggle={onToggleGroup}
      />
    )
  if (row.type === 'group')
    return (
      <li className='flex min-w-0 items-center gap-2 pb-4'>
        <Button
          variant='ghost'
          size='sm'
          onClick={() => onToggleGroup(row.key)}
          aria-expanded={row.hidden.length === 0}
        >
          {row.hidden.length > 0 ? <ChevronsDown /> : <ChevronsUp />}
          {row.hidden.length > 0
            ? `+${row.hidden.length} similar: ${FEED_CATEGORY_LABEL[row.category]}`
            : 'Collapse'}
        </Button>
      </li>
    )
  const { line } = row
  if (line.stream)
    return (
      <StreamLineView
        line={line}
        open={row.open}
        last={last}
        stamp={stamp(line, row.repeatedEpoch)}
        onToggle={onToggleGroup}
      />
    )
  return (
    <TimelineItem
      icon={FEED_SYMBOL_ICON[line.symbol]}
      tone={line.tone}
      title={<MentionText text={line.title} />}
      timestamp={stamp(line, row.repeatedEpoch)}
      last={last}
      framed
    >
      {(line.detail ||
        line.link ||
        line.category ||
        line.meta.chips.length > 0 ||
        line.meta.rarity) && (
        <div className='flex min-w-0 flex-col gap-1'>
          {(line.meta.rarity || line.meta.chips.length > 0) && (
            <div className='flex min-w-0 flex-wrap items-center gap-1'>
              {isRarity(line.meta.rarity) && (
                <RarityBadge rarity={line.meta.rarity} size='sm' />
              )}
              {line.meta.chips.map((chip) => (
                <Badge key={chip} size='sm' variant='outline'>
                  {chip}
                </Badge>
              ))}
            </div>
          )}
          {line.detail && (
            <Muted truncate={3}>
              <MentionText text={line.detail} />
            </Muted>
          )}
          {(line.link || line.category) && (
            <div className='flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1'>
              <LineLink line={line} />
              {line.category && (
                <Label>{FEED_CATEGORY_LABEL[line.category]}</Label>
              )}
            </div>
          )}
        </div>
      )}
    </TimelineItem>
  )
}

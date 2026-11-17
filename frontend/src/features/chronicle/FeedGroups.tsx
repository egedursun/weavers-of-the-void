import { useState } from 'react'
import { ChevronDown, Layers } from 'lucide-react'
import { type components } from '@/api/generated/schema'
import { plural } from '@/lib/units'
import { Button } from '@/components/ui/button'
import { ShowMore, useShowMore } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { ChronicleEntry } from './ChronicleEntry'

type Line = components['schemas']['ChronicleLineRecord']
type Group = components['schemas']['ChronicleFeedGroup']
const FEED_SHOWN = 40
const GROUP_SHOWN = 12

type Block =
  { kind: 'line'; line: Line } | { kind: 'group'; lines: Line[]; size: number }

function feedBlocks(lines: readonly Line[], groups: readonly Group[]): Block[] {
  const groupOf = new Map<number, number>()
  groups.forEach((group, index) =>
    group.line_ids.forEach((id) => groupOf.set(id, index))
  )
  const members = new Map<number, Line[]>()
  for (const line of lines) {
    const index = groupOf.get(line.id)
    if (index !== undefined)
      members.set(index, [...(members.get(index) ?? []), line])
  }
  const placed = new Set<number>()
  const blocks: Block[] = []
  for (const line of lines) {
    const index = groupOf.get(line.id)
    const shown = index === undefined ? [] : (members.get(index) ?? [])
    if (index === undefined || shown.length < 2) {
      blocks.push({ kind: 'line', line })
      continue
    }
    if (placed.has(index)) continue
    placed.add(index)
    blocks.push({
      kind: 'group',
      lines: shown,
      size: groups[index]?.size ?? shown.length,
    })
  }
  return blocks
}

function GroupEntry({
  lines,
  size,
  kindLabel,
  highlightLine,
}: {
  lines: Line[]
  size: number
  kindLabel: string | undefined
  highlightLine?: number | null
}) {
  const [open, setOpen] = useState(
    lines.some((line) => line.id === highlightLine)
  )
  const inner = useShowMore(lines, GROUP_SHOWN)
  const first = lines[0]
  return (
    <li className='flex min-w-0 flex-col gap-1 rounded-md border surface-sheen border-gild/60 bg-card p-2'>
      <div className='flex min-w-0 items-center gap-2'>
        <Layers
          aria-hidden='true'
          className='size-icon-sm shrink-0 text-primary'
        />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Text weight='semibold'>{`${plural(size, 'happening')} of this kind`}</Text>
          <Muted variant='caption' truncate>
            {first ? `${kindLabel ? `${kindLabel} · ` : ''}${first.text}` : ''}
          </Muted>
        </div>
        <Button
          variant='ghost'
          size='sm'
          aria-expanded={open}
          onClick={() => setOpen((current) => !current)}
        >
          <ChevronDown
            aria-hidden='true'
            className={
              open ? 'rotate-180 transition-transform' : 'transition-transform'
            }
          />
          {open ? 'Fold them' : 'Show every one'}
        </Button>
      </div>
      {open && (
        <>
          <ol className='flex min-w-0 flex-col gap-1'>
            {inner.visible.map((line) => (
              <ChronicleEntry
                key={line.id}
                line={line}
                showEpoch={false}
                kindLabel={kindLabel}
                highlighted={highlightLine === line.id}
              />
            ))}
          </ol>
          <ShowMore state={inner} noun={['happening', 'happenings']} />
        </>
      )}
    </li>
  )
}

export function FeedLines({
  lines,
  groups,
  kindLabels,
  highlightLine,
}: {
  lines: readonly Line[]
  groups: readonly Group[]
  kindLabels: Map<string, string>
  highlightLine?: number | null
}) {
  const blocks = useShowMore(feedBlocks(lines, groups), FEED_SHOWN)
  return (
    <>
      <ol className='flex min-w-0 flex-col gap-1'>
        {blocks.visible.map((block) =>
          block.kind === 'line' ? (
            <ChronicleEntry
              key={block.line.id}
              line={block.line}
              showEpoch={false}
              kindLabel={kindLabels.get(block.line.kind)}
              highlighted={highlightLine === block.line.id}
            />
          ) : (
            <GroupEntry
              key={`group-${block.lines[0]?.id}`}
              lines={block.lines}
              size={block.size}
              kindLabel={
                block.lines[0] ? kindLabels.get(block.lines[0].kind) : undefined
              }
              highlightLine={highlightLine}
            />
          )
        )}
      </ol>
      <ShowMore state={blocks} noun={['entry', 'entries']} />
    </>
  )
}

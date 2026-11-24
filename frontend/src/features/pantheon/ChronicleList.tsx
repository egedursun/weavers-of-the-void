import { ScrollText } from 'lucide-react'
import {
  EmptyState,
  ExpandableText,
  Section,
  ShowMore,
  Timeline,
  TimelineItem,
  useShowMore,
} from '@/components/domain'
import { MentionText } from '@/components/domain/MentionText'
import { chronicleKindIcon } from '@/components/domain/chronicleKindIcons'
import { OlderLinesButton } from '@/features/chronicle/OlderLinesButton'
import { type OlderLines } from '@/features/chronicle/api'
import { useLinkTargets } from '@/features/chronicle/linkTargets'
import { type ChronicleLine } from './api'

const LINES_SHOWN = 8
const LINES_STEP = 12

function LineText({ line }: { line: ChronicleLine }) {
  const targets = useLinkTargets(line.entity_ids ?? [])
  return (
    <ExpandableText lines={4}>
      <MentionText text={line.text} targets={targets} />
    </ExpandableText>
  )
}

type ChronicleListProps = {
  sectionId: string
  title: string
  description?: string
  lines: ChronicleLine[]
  emptyTitle: string
  emptyText: string
  newestFirst?: boolean
  older?: OlderLines
}

export function ChronicleList({
  sectionId,
  title,
  description,
  lines,
  emptyTitle,
  emptyText,
  newestFirst = true,
  older,
}: ChronicleListProps) {
  const known = older ? [...lines, ...older.lines] : lines
  const ordered = newestFirst ? [...known].sort((a, b) => b.id - a.id) : known
  const page = useShowMore(ordered, LINES_SHOWN, LINES_STEP)
  return (
    <Section id={sectionId} title={title} description={description} level={3}>
      {ordered.length === 0 ? (
        <EmptyState
          icon={ScrollText}
          size='compact'
          title={emptyTitle}
          description={emptyText}
        />
      ) : (
        <div className='flex min-w-0 flex-col gap-3'>
          <Timeline label={title}>
            {page.visible.map((line, index) => (
              <TimelineItem
                key={line.id}
                icon={chronicleKindIcon(line.kind)}
                title={`Epoch ${line.epoch}`}
                timestamp={line.year !== null ? `Year ${line.year}` : undefined}
                last={index === page.visible.length - 1}
              >
                <LineText line={line} />
              </TimelineItem>
            ))}
          </Timeline>
          <ShowMore state={page} noun={['entry', 'entries']} />
          {older && <OlderLinesButton older={older} />}
        </div>
      )}
    </Section>
  )
}

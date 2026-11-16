import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import { ArrowDown, Eraser, Radio } from 'lucide-react'
import { plural } from '@/lib/units'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { OrnateFrame } from '@/components/ui/ornate'
import { EmptyState, Timeline } from '@/components/domain'
import { Label, Muted, SectionTitle } from '@/components/typography'
import { ImageQueueFeed } from '@/features/images/ImageQueueFeed'
import { useImageGenStore } from '@/features/images/imageGenState'
import { FeedFilters } from './FeedFilters'
import { FeedRowView } from './FeedLine'
import { FeedSoundControls } from './FeedSoundControls'
import { LiveFeedHeader } from './LiveFeedHeader'
import { buildRows, matchesFilter, presentCategories } from './feedModel'
import { useFeed } from './feedStore'

const STICKY_DISTANCE_PX = 48

type LiveFeedPanelProps = {
  layout?: 'card' | 'fill'
  showHeader?: boolean
}

function useVisibleRows() {
  const lines = useFeed((state) => state.lines)
  const actor = useFeed((state) => state.actor)
  const selected = useFeed((state) => state.categories)
  const expanded = useFeed((state) => state.expanded)
  return useMemo(() => {
    const filter = { actor, categories: new Set(selected) }
    const visible = lines.filter((line) => matchesFilter(line, filter))
    return {
      total: lines.length,
      categories: presentCategories(lines),
      visible: visible.length,
      rows: buildRows(visible, new Set(expanded)),
    }
  }, [actor, expanded, lines, selected])
}

export function LiveFeedPanel({
  layout = 'card',
  showHeader = false,
}: LiveFeedPanelProps) {
  const { total, categories, visible, rows } = useVisibleRows()
  const restored = useFeed((state) => state.restored)
  const toggleGroup = useFeed((state) => state.toggleGroup)
  const clear = useFeed((state) => state.clear)
  const imageLines = useImageGenStore((store) => store.lines.length)
  const scroller = useRef<HTMLDivElement>(null)
  const sticky = useRef(true)
  const [seen, setSeen] = useState(visible)
  const unseen = Math.max(0, visible - seen)

  const toBottom = useCallback(() => {
    const element = scroller.current
    if (element) element.scrollTop = element.scrollHeight
    sticky.current = true
    setSeen(visible)
  }, [visible])

  useLayoutEffect(() => {
    if (!sticky.current) return
    const element = scroller.current
    if (element) element.scrollTop = element.scrollHeight
  }, [rows])

  useEffect(() => {
    if (sticky.current || visible < seen) setSeen(visible)
  }, [seen, visible])

  const onScroll = () => {
    const element = scroller.current
    if (!element) return
    const distance =
      element.scrollHeight - element.scrollTop - element.clientHeight
    sticky.current = distance <= STICKY_DISTANCE_PX
    if (sticky.current) setSeen(visible)
  }

  const panel = (
    <section
      aria-label='Live feed'
      data-feature='live-feed'
      className={cn(
        'flex min-h-0 min-w-0 flex-col gap-3',
        layout === 'card' && 'h-full',
        layout === 'fill' && 'flex-1'
      )}
    >
      {showHeader && <LiveFeedHeader titled={layout !== 'card'} />}
      <div
        data-feature='live-feed-toolbar'
        className='flex min-w-0 flex-col gap-2 rounded-md plate-track p-2'
      >
        <FeedFilters categories={categories} />
        <div className='flex min-w-0 items-center justify-between gap-2 border-t pt-2'>
          <Muted variant='caption' truncate>
            {total === 0
              ? 'No events yet'
              : visible === total
                ? `${total} ${total === 1 ? 'event' : 'events'}`
                : `Showing ${visible} of ${plural(total, 'event', 'events')}`}
          </Muted>
          <div className='flex shrink-0 items-center gap-1'>
            <FeedSoundControls />
            <Button
              variant='outline'
              size='icon-sm'
              aria-label='Clear the feed'
              onClick={clear}
              disabled={total === 0}
              disabledReason='The feed is already empty'
            >
              <Eraser />
            </Button>
          </div>
        </div>
      </div>
      {restored && total > 0 && (
        <Muted variant='caption'>
          Earlier events were restored from the server.
        </Muted>
      )}
      {imageLines > 0 && (
        <div
          data-feature='feed-image-queue'
          className='flex min-w-0 flex-col gap-2 rounded-md border surface-framed border-gild/70 bg-card p-3'
        >
          <Label variant='overline'>Images</Label>
          <ImageQueueFeed />
        </div>
      )}
      <div className='relative flex min-h-0 min-w-0 flex-1 flex-col'>
        <div
          ref={scroller}
          onScroll={onScroll}
          tabIndex={0}
          aria-label='Feed lines'
          className={cn(
            'min-h-0 min-w-0 overflow-y-auto overscroll-contain rounded-md outline-none focus-visible:ring-2 focus-visible:ring-ring/50',
            layout === 'card' ? 'h-96' : 'flex-1'
          )}
        >
          {rows.length === 0 ? (
            <EmptyState
              size='compact'
              icon={Radio}
              title={total === 0 ? 'Quiet' : 'Nothing matches this filter'}
              description={
                total === 0
                  ? 'When a son acts, the world turns or Fate speaks, it flows here.'
                  : 'Pick another actor or category to see more lines.'
              }
            />
          ) : (
            <Timeline label='Live feed lines'>
              {rows.map((row, index) => (
                <FeedRowView
                  key={row.type === 'line' ? row.line.id : row.key}
                  row={row}
                  last={index === rows.length - 1}
                  onToggleGroup={toggleGroup}
                />
              ))}
            </Timeline>
          )}
        </div>
        {unseen > 0 && (
          <div className='pointer-events-none absolute inset-x-0 bottom-2 flex justify-center'>
            <Button
              size='sm'
              className='pointer-events-auto'
              onClick={toBottom}
            >
              <ArrowDown />
              {`${unseen} new ${unseen === 1 ? 'event' : 'events'}`}
            </Button>
          </div>
        )}
      </div>
    </section>
  )
  if (layout !== 'card') return panel
  return (
    <OrnateFrame
      footCrest
      className='h-full px-5 pb-9 sm:px-9'
      nameplate={
        <SectionTitle level={2} truncate className='text-gilded'>
          Live feed
        </SectionTitle>
      }
    >
      {panel}
    </OrnateFrame>
  )
}

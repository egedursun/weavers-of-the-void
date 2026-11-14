import { useEffect, useId, useState } from 'react'
import { Layers, X, ZoomIn } from 'lucide-react'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { PagedList } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { NodeAvatar } from '@/features/images/NodeAvatar'

export type StackItem = {
  id: number
  name: string
  detail: string
  dead: boolean
}

export type StackSection = { title: string; items: StackItem[] }

export type StackPopup = {
  x: number
  y: number
  title: string
  summary: string
  sections: StackSection[]
  centre: { x: number; y: number } | null
}

type MapStackOverlayProps = {
  popup: StackPopup
  width: number
  height: number
  onOpen: (id: number) => void
  onZoom: (centre: { x: number; y: number }) => void
  onClose: () => void
}

const POPUP_WIDTH = 336
const EDGE = 12
const OFFSET = 16
const SEARCH_FROM = 8
const INITIAL = 12
const STEP = 24

function matches(item: StackItem, query: string): boolean {
  if (!query) return true
  const needle = query.toLocaleLowerCase('en-US')
  return (
    item.name.toLocaleLowerCase('en-US').includes(needle) ||
    item.detail.toLocaleLowerCase('en-US').includes(needle)
  )
}

export function MapStackOverlay({
  popup,
  width,
  height,
  onOpen,
  onZoom,
  onClose,
}: MapStackOverlayProps) {
  const searchId = useId()
  const [query, setQuery] = useState('')
  const total = popup.sections.reduce(
    (sum, section) => sum + section.items.length,
    0
  )
  const left = Math.min(
    Math.max(EDGE, popup.x + OFFSET),
    Math.max(EDGE, width - POPUP_WIDTH - EDGE)
  )
  const top = EDGE
  const maxHeight = Math.max(160, height - EDGE * 2)

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const sections = popup.sections
    .map((section) => ({
      ...section,
      items: section.items.filter((item) => matches(item, query.trim())),
    }))
    .filter((section) => section.items.length > 0)

  return (
    <div
      role='dialog'
      aria-label={popup.title}
      data-map-stack
      className='absolute flex w-84 max-w-full min-w-0 flex-col gap-3 overflow-hidden rounded-lg border bg-popover p-3 text-popover-foreground shadow-lg'
      style={{ left, top, maxHeight }}
    >
      <div className='flex min-w-0 items-start gap-2'>
        <Layers
          aria-hidden='true'
          className='size-icon-md shrink-0 text-primary'
        />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Text as='span' weight='semibold' truncate={2}>
            {popup.title}
          </Text>
          <Muted variant='caption'>{popup.summary}</Muted>
        </div>
        <Button
          size='icon-sm'
          variant='ghost'
          aria-label='Close'
          onClick={onClose}
        >
          <X />
        </Button>
      </div>
      {(total >= SEARCH_FROM || popup.centre) && (
        <div className='flex min-w-0 items-center gap-2'>
          {total >= SEARCH_FROM && (
            <Input
              id={searchId}
              aria-label='Filter the records here'
              placeholder={`Filter ${plural(total, 'record', 'records')}…`}
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              className='min-w-0 flex-1'
            />
          )}
          {popup.centre && (
            <Button
              size='sm'
              variant='outline'
              onClick={() => popup.centre && onZoom(popup.centre)}
            >
              <ZoomIn />
              Zoom in
            </Button>
          )}
        </div>
      )}
      <div className='flex min-h-0 min-w-0 flex-1 flex-col gap-4 overflow-y-auto overscroll-contain'>
        {sections.length === 0 && <Muted>Nothing here matches.</Muted>}
        {sections.map((section) => (
          <div key={section.title} className='flex min-w-0 flex-col gap-1.5'>
            <Label variant='overline'>{`${section.title} · ${section.items.length.toLocaleString('en-US')}`}</Label>
            <PagedList
              items={section.items}
              initial={INITIAL}
              step={STEP}
              noun={['record', 'records']}
              className='flex min-w-0 flex-col gap-0.5'
              itemKey={(item) => item.id}
            >
              {(item) => (
                <li className='min-w-0'>
                  <Button
                    variant='ghost'
                    size='tile'
                    onClick={() => onOpen(item.id)}
                  >
                    <NodeAvatar id={item.id} name={item.name} />
                    <span className='flex min-w-0 flex-1 flex-col'>
                      <Text as='span' weight='medium' truncate>
                        {item.name}
                      </Text>
                      <Muted as='span' variant='caption' truncate={2}>
                        {item.detail}
                      </Muted>
                    </span>
                    {item.dead && (
                      <Badge size='sm' variant='secondary'>
                        Fallen
                      </Badge>
                    )}
                  </Button>
                </li>
              )}
            </PagedList>
          </div>
        ))}
      </div>
    </div>
  )
}

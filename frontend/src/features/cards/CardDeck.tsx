import {
  type KeyboardEvent,
  type PointerEvent,
  useEffect,
  useRef,
  useState,
} from 'react'
import {
  ChevronLeft,
  ChevronRight,
  Download,
  Hand,
  Maximize2,
  Repeat2,
  Shuffle,
} from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Label, Muted } from '@/components/typography'
import { LoreCard } from './LoreCard'
import { SealedPack } from './SealedPack'
import { type CharacterCard } from './api'
import { sealedIn, useCardSeals, useSealed } from './sealStore'

const DRAG_START = 8
const SWIPE_SHARE = 0.22
const PREFETCH_AHEAD = 6
const BEHIND = 2

type CardDeckProps = {
  visible: CharacterCard[]
  total: number
  index: number
  onIndex: (index: number) => void
  hasMore: boolean
  loadingMore: boolean
  onLoadMore: () => void
  onOpen: (index: number) => void
  onDownload: (card: CharacterCard) => void
  downloadReason: string | null
}

type Drag = { id: number; x: number; y: number; dx: number; moved: boolean }

const SEALED_REASON = 'Open the pack first.'

function DeckFace({
  card,
  flipped,
  tilt,
}: {
  card: CharacterCard
  flipped: boolean
  tilt: boolean
}) {
  const sealed = useSealed(card.node_id)
  if (sealed) return <SealedPack aria-label='A sealed pack' />
  return <LoreCard card={card} flipped={flipped} tilt={tilt} />
}

function depthOf(offset: number): string {
  if (offset < 0) return 'gone'
  return String(offset)
}

export function CardDeck({
  visible,
  total,
  index,
  onIndex,
  hasMore,
  loadingMore,
  onLoadMore,
  onOpen,
  onDownload,
  downloadReason,
}: CardDeckProps) {
  const [flipped, setFlipped] = useState<number | null>(null)
  const drag = useRef<Drag | null>(null)
  const top = useRef<HTMLDivElement>(null)
  const current = visible[index]
  const sealed = useCardSeals((state) =>
    current ? sealedIn(state, current.node_id) : false
  )
  const last = visible.length - 1
  const atEnd = index >= last && !hasMore

  useEffect(() => {
    if (hasMore && !loadingMore && index >= visible.length - PREFETCH_AHEAD)
      onLoadMore()
  }, [hasMore, loadingMore, index, visible.length, onLoadMore])

  const go = (step: number) => {
    const next = index + step
    if (next < 0 || next > last) return
    setFlipped(null)
    onIndex(next)
  }

  const flip = () => {
    if (sealed) {
      onOpen(index)
      return
    }
    setFlipped((value) =>
      current && value !== current.node_id ? current.node_id : null
    )
  }

  const release = () => {
    const node = top.current
    if (!node) return
    node.removeAttribute('data-dragging')
    node.style.setProperty('--drag', '0')
  }

  const onPointerDown = (event: PointerEvent<HTMLDivElement>) => {
    if (event.button !== 0) return
    drag.current = {
      id: event.pointerId,
      x: event.clientX,
      y: event.clientY,
      dx: 0,
      moved: false,
    }
  }

  const onPointerMove = (event: PointerEvent<HTMLDivElement>) => {
    const state = drag.current
    const node = top.current
    if (!state || !node || state.id !== event.pointerId) return
    const dx = event.clientX - state.x
    const dy = event.clientY - state.y
    if (!state.moved) {
      if (Math.abs(dx) < DRAG_START || Math.abs(dx) < Math.abs(dy)) return
      state.moved = true
      event.currentTarget.setPointerCapture(event.pointerId)
      node.setAttribute('data-dragging', '')
    }
    state.dx = dx
    node.style.setProperty('--drag', String(dx))
  }

  const onPointerUp = (event: PointerEvent<HTMLDivElement>) => {
    const state = drag.current
    drag.current = null
    if (!state || state.id !== event.pointerId) return
    const width = event.currentTarget.getBoundingClientRect().width
    release()
    if (!state.moved) {
      flip()
      return
    }
    if (Math.abs(state.dx) > width * SWIPE_SHARE) go(state.dx < 0 ? 1 : -1)
  }

  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'ArrowRight') go(1)
    else if (event.key === 'ArrowLeft') go(-1)
    else if (event.key === 'Enter') onOpen(index)
    else if (event.key === ' ' || event.key.toLowerCase() === 'f') flip()
    else return
    event.preventDefault()
  }

  const shuffle = () => {
    if (visible.length < 2) return
    const offset = 1 + Math.floor(Math.random() * (visible.length - 1))
    setFlipped(null)
    onIndex((index + offset) % visible.length)
  }

  if (!current) return null
  const spread = visible
    .map((card, position) => ({ card, offset: position - index }))
    .slice(Math.max(0, index - 1), index + BEHIND + 1)
  return (
    <div className='flex min-w-0 flex-col items-center gap-5'>
      <div
        className='lore-deck-stage'
        role='region'
        aria-roledescription='card deck'
        aria-label={
          sealed
            ? `Card ${index + 1} of ${total}: a sealed pack. Swipe or press the arrow keys to move, enter or space to open the pack.`
            : `Card ${index + 1} of ${total}: ${current.name}. Swipe or press the arrow keys to move, space to turn the card over, enter to open it.`
        }
        tabIndex={0}
        onKeyDown={onKeyDown}
      >
        {spread.map(({ card, offset }) => (
          <div
            key={card.node_id}
            ref={offset === 0 ? top : undefined}
            className='lore-deck-slot'
            data-depth={depthOf(offset)}
            aria-hidden={offset !== 0 || undefined}
            onPointerDown={offset === 0 ? onPointerDown : undefined}
            onPointerMove={offset === 0 ? onPointerMove : undefined}
            onPointerUp={offset === 0 ? onPointerUp : undefined}
            onPointerCancel={offset === 0 ? release : undefined}
          >
            <DeckFace
              card={card}
              flipped={flipped === card.node_id}
              tilt={offset === 0}
            />
          </div>
        ))}
      </div>
      <div className='flex w-full max-w-md min-w-0 flex-col gap-2'>
        <div className='flex min-w-0 items-center justify-between gap-2'>
          <Label>{`Card ${formatInteger(index + 1)} of ${formatInteger(total)}`}</Label>
          <Muted variant='caption' truncate>
            {loadingMore
              ? 'Drawing more cards…'
              : sealed
                ? 'A sealed pack'
                : current.name}
          </Muted>
        </div>
        <Progress
          value={total > 0 ? ((index + 1) / total) * 100 : 0}
          aria-label='Place in the deck'
        />
      </div>
      <div className='flex min-w-0 flex-wrap items-center justify-center gap-2'>
        <Button
          variant='outline'
          size='icon'
          aria-label='Previous card'
          onClick={() => go(-1)}
          disabled={index === 0}
          disabledReason='This is the first card of the deck.'
        >
          <ChevronLeft />
        </Button>
        <Button
          variant='outline'
          onClick={flip}
          disabled={sealed}
          disabledReason={SEALED_REASON}
        >
          <Repeat2 />
          {flipped === current.node_id ? 'Show the front' : 'Turn over'}
        </Button>
        {sealed ? (
          <Button onClick={() => onOpen(index)}>
            <Hand />
            Open the pack
          </Button>
        ) : (
          <Button variant='outline' onClick={() => onOpen(index)}>
            <Maximize2 />
            Inspect
          </Button>
        )}
        <Button
          variant='outline'
          onClick={() => onDownload(current)}
          disabled={sealed || downloadReason !== null}
          disabledReason={
            sealed ? SEALED_REASON : (downloadReason ?? undefined)
          }
        >
          <Download />
          Save as image
        </Button>
        <Button
          variant='outline'
          size='icon'
          aria-label='Draw a random card'
          onClick={shuffle}
          disabled={visible.length < 2}
          disabledReason='There is only one card in this deck.'
        >
          <Shuffle />
        </Button>
        <Button
          variant='outline'
          size='icon'
          aria-label='Next card'
          onClick={() => go(1)}
          disabled={index >= last}
          disabledReason={
            atEnd
              ? 'This is the last card of the deck.'
              : 'The next cards are still being drawn.'
          }
        >
          <ChevronRight />
        </Button>
      </div>
      <Muted variant='caption'>
        {sealed
          ? 'Swipe or use the arrow keys. Tap the pack to open it.'
          : 'Swipe the card or use the arrow keys. Tap it to turn it over.'}
      </Muted>
    </div>
  )
}

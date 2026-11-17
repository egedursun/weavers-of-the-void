import { type KeyboardEvent } from 'react'
import { Globe2, type LucideIcon } from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { cn } from '@/lib/utils'
import { Medallion } from '@/components/domain'
import { Label, SectionTitle } from '@/components/typography'
import { LoreCard } from './LoreCard'
import { type CharacterCard } from './api'
import { FRAME_ICON, isDivine } from './cardModel'

type CardBinderProps = {
  visible: CharacterCard[]
  divineTotal: number
  soulsTotal: number
  onOpen: (index: number) => void
}

type Placed = { card: CharacterCard; index: number }

function Shelf({
  title,
  icon,
  total,
  placed,
  wide,
  onOpen,
}: {
  title: string
  icon: LucideIcon
  total: number
  placed: Placed[]
  wide: boolean
  onOpen: (index: number) => void
}) {
  const pressed = (event: KeyboardEvent<HTMLDivElement>, index: number) => {
    if (event.key !== 'Enter' && event.key !== ' ') return
    event.preventDefault()
    onOpen(index)
  }
  return (
    <section className='flex min-w-0 flex-col gap-4' aria-label={title}>
      <div className='flex min-w-0 items-center gap-3 border-b border-gild/40 pb-2'>
        <Medallion icon={icon} size='sm' />
        <SectionTitle level={3} truncate className='flex-1 text-gilded'>
          {title}
        </SectionTitle>
        <Label>{`${formatInteger(placed.length)} of ${formatInteger(total)} shown`}</Label>
      </div>
      <div
        role='list'
        aria-label={title}
        className={cn(
          'grid min-w-0 grid-cols-2 gap-5',
          wide ? 'md:grid-cols-3' : 'sm:grid-cols-3 xl:grid-cols-4'
        )}
      >
        {placed.map(({ card, index }) => (
          <div
            key={card.node_id}
            role='listitem'
            className='lore-card-enter min-w-0'
          >
            <LoreCard
              card={card}
              role='button'
              tabIndex={0}
              aria-label={`Inspect the card of ${card.name}`}
              className='lore-binder-card'
              onClick={() => onOpen(index)}
              onKeyDown={(event) => pressed(event, index)}
            />
          </div>
        ))}
      </div>
    </section>
  )
}

export function CardBinder({
  visible,
  divineTotal,
  soulsTotal,
  onOpen,
}: CardBinderProps) {
  const placed = visible.map((card, index) => ({ card, index }))
  const divine = placed.filter(({ card }) => isDivine(card))
  const souls = placed.filter(({ card }) => !isDivine(card))
  return (
    <div className='flex min-w-0 flex-col gap-8'>
      {divine.length > 0 && (
        <Shelf
          title='The divine'
          icon={FRAME_ICON.son}
          total={divineTotal}
          placed={divine}
          wide
          onOpen={onOpen}
        />
      )}
      {souls.length > 0 && (
        <Shelf
          title='Souls of the worlds'
          icon={Globe2}
          total={soulsTotal}
          placed={souls}
          wide={false}
          onOpen={onOpen}
        />
      )}
    </div>
  )
}

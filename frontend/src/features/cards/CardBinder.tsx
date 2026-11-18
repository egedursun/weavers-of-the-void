import { type KeyboardEvent } from 'react'
import { Globe2, type LucideIcon, Package } from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Medallion } from '@/components/domain'
import { Label, SectionTitle } from '@/components/typography'
import { LoreCard } from './LoreCard'
import { SealedPack } from './SealedPack'
import { type CharacterCard } from './api'
import { FRAME_ICON, isDivine } from './cardModel'
import { useCardSeals, useSealed } from './sealStore'

type CardBinderProps = {
  visible: CharacterCard[]
  divineTotal: number
  soulsTotal: number
  onOpen: (index: number) => void
}

type Placed = { card: CharacterCard; index: number }

function BinderSlot({
  card,
  index,
  onOpen,
}: {
  card: CharacterCard
  index: number
  onOpen: (index: number) => void
}) {
  const sealed = useSealed(card.node_id)
  const seal = useCardSeals((state) => state.seal)
  const pressed = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key !== 'Enter' && event.key !== ' ') return
    event.preventDefault()
    onOpen(index)
  }
  if (sealed)
    return (
      <div key='sealed' className='lore-seal-swap'>
        <SealedPack
          role='button'
          tabIndex={0}
          aria-label='Open a sealed pack'
          className='lore-binder-card'
          onClick={() => onOpen(index)}
          onKeyDown={pressed}
        />
      </div>
    )
  return (
    <div key='open' className='lore-seal-swap lore-binder-slot'>
      <LoreCard
        card={card}
        role='button'
        tabIndex={0}
        aria-label={`Inspect the card of ${card.name}`}
        className='lore-binder-card'
        onClick={() => onOpen(index)}
        onKeyDown={pressed}
      />
      <span className='lore-binder-reseal'>
        <Button
          variant='outline'
          size='icon-sm'
          aria-label={`Seal the card of ${card.name} back in its pack`}
          title='Seal it back in its pack'
          onClick={() => seal(card.node_id)}
        >
          <Package />
        </Button>
      </span>
    </div>
  )
}

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
            <BinderSlot card={card} index={index} onOpen={onOpen} />
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

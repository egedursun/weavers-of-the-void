import {
  Award,
  Clock,
  Gem,
  type LucideIcon,
  Package,
  Skull,
  Stamp,
  TrendingUp,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { RARITIES, RARITY_LABEL } from '@/constants/rarity'
import { Medallion, RarityIcon } from '@/components/domain'
import { RARITY_TEXT_CLASS } from '@/components/domain/rarityClasses'
import { Label, Muted, Text } from '@/components/typography'
import { type CardMaterial, MATERIAL_LABEL } from './cardModel'

const DIVINE_FRAMES: {
  material: CardMaterial
  title: string
  text: string
}[] = [
  {
    material: 'sovereign',
    title: 'The Creator',
    text: 'White gold with a holo foil and a dusting of light.',
  },
  {
    material: 'epic',
    title: 'Children',
    text: 'Their own rarity metal, gilded corners, a halo and a gilded name.',
  },
  {
    material: 'obsidian',
    title: 'Foreign gods',
    text: 'Obsidian with gilded corners: they stand outside the tiers.',
  },
]

const ANATOMY: { icon: LucideIcon; title: string; text: string }[] = [
  {
    icon: TrendingUp,
    title: 'Gem at the top left',
    text: 'The level of a child, or the power level of a mortal or being.',
  },
  {
    icon: Clock,
    title: 'Clock dials',
    text: 'The epoch it was born in; a second dial is the epoch it fell in, and the Creator\u2019s dial is endless.',
  },
  {
    icon: Skull,
    title: '† before a name',
    text: 'The soul has fallen; its card stays in the collection.',
  },
  {
    icon: Gem,
    title: 'Gems at the foot',
    text: 'Its two headline values, each with the icon used across the pantheon.',
  },
  {
    icon: Award,
    title: 'Seal at the foot',
    text: 'Its rarity; turn the card over for every value and power.',
  },
  {
    icon: Package,
    title: 'Sealed packs',
    text: 'A card you have not opened yet waits in a sealed pack. Tear it open to see whose card it is, and seal it back from the card whenever you like.',
  },
  {
    icon: Stamp,
    title: 'Engraved emblem',
    text: 'A soul with no likeness yet carries an engraved emblem in its metal: its initial, its kind on the crown and a jewel for each step of rarity.',
  },
]

function Swatch({ material }: { material: CardMaterial }) {
  return (
    <span className='lore-swatch' data-material={material} aria-hidden='true' />
  )
}

export function CardLegend() {
  return (
    <div className='grid min-w-0 grid-cols-1 gap-4 lg:grid-cols-3'>
      <div className='flex min-w-0 flex-col gap-3 rounded-md border surface-framed border-gild/70 bg-card p-3'>
        <Label variant='overline'>Rarity is the metal of the frame</Label>
        <ul className='grid min-w-0 grid-cols-2 gap-3'>
          {RARITIES.map((rarity) => (
            <li key={rarity} className='flex min-w-0 items-center gap-2'>
              <Swatch material={rarity} />
              <span className='flex min-w-0 flex-col'>
                <span
                  className={cn(
                    'inline-flex min-w-0 items-center gap-1',
                    RARITY_TEXT_CLASS[rarity]
                  )}
                >
                  <RarityIcon rarity={rarity} className='size-icon-xs' />
                  <Text as='span' weight='semibold' tone='inherit' truncate>
                    {RARITY_LABEL[rarity]}
                  </Text>
                </span>
                <Muted variant='caption' truncate>
                  {MATERIAL_LABEL[rarity]}
                </Muted>
              </span>
            </li>
          ))}
        </ul>
        <Muted variant='caption'>
          Epic and higher cards carry a holo foil; legendary frames sweep with
          light and mythic frames shift through every colour.
        </Muted>
      </div>
      <div className='flex min-w-0 flex-col gap-3 rounded-md border surface-framed border-gild/70 bg-card p-3'>
        <Label variant='overline'>Gods have frames of their own</Label>
        <ul className='flex min-w-0 flex-col gap-3'>
          {DIVINE_FRAMES.map((frame) => (
            <li key={frame.title} className='flex min-w-0 items-center gap-3'>
              <Swatch material={frame.material} />
              <span className='flex min-w-0 flex-col'>
                <Text weight='semibold'>{frame.title}</Text>
                <Muted variant='caption'>{frame.text}</Muted>
              </span>
            </li>
          ))}
        </ul>
      </div>
      <div className='flex min-w-0 flex-col gap-3 rounded-md border surface-framed border-gild/70 bg-card p-3'>
        <Label variant='overline'>Reading a card</Label>
        <ul className='flex min-w-0 flex-col gap-3'>
          {ANATOMY.map((item) => (
            <li key={item.title} className='flex min-w-0 items-start gap-3'>
              <Medallion icon={item.icon} size='sm' />
              <span className='flex min-w-0 flex-col'>
                <Text weight='semibold'>{item.title}</Text>
                <Muted variant='caption'>{item.text}</Muted>
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}

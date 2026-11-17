import { type HTMLAttributes, type ReactNode, useRef } from 'react'
import { type LucideIcon, ScrollText, Sparkles, Star } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useFitText } from '@/hooks/useFitText'
import { useReducedMotion } from '@/hooks/useReducedMotion'
import { Picture, RarityIcon, Sigil } from '@/components/domain'
import { type ThumbnailWidth } from '@/features/images/media'
import { useLabels } from '@/features/pantheon/labels'
import { mediaUrl } from '@/features/pantheon/media'
import { type CharacterCard, type CharacterCardStat } from './api'
import {
  type CardSide,
  FRAME_ICON,
  epochLine,
  footValues,
  frameOf,
  isDivine,
  materialOf,
  rankOf,
  statFill,
  statGroups,
  statMeta,
  statText,
  tierLabel,
  typeLine,
} from './cardModel'
import { useCardTilt } from './useCardTilt'
import { useFitLines } from './useFitLines'

export const CARD_ART_WIDTH: ThumbnailWidth = 640

const DIAL_TICKS = [0, 90, 180, 270]
const ENDLESS = '\u221E'
const CORNERS = ['tl', 'tr', 'bl', 'br'] as const

type FaceProps = {
  card: CharacterCard
  artWidth: ThumbnailWidth
  hidden?: boolean
}

function dialSize(value: number | string): number {
  if (value === ENDLESS) return 20
  const digits = String(value).length
  if (digits <= 2) return 15
  return digits === 3 ? 12 : 9.5
}

function Dial({ value, fallen }: { value: number | string; fallen?: boolean }) {
  return (
    <svg
      viewBox='0 0 40 40'
      className='lore-card-dial'
      data-fallen={fallen || undefined}
      aria-hidden='true'
    >
      <circle cx='20' cy='20' r='17.5' className='lore-card-dial-rim' />
      {DIAL_TICKS.map((angle) => (
        <line
          key={angle}
          x1='20'
          y1='3.6'
          x2='20'
          y2='7.4'
          transform={`rotate(${angle} 20 20)`}
          className='lore-card-dial-tick'
        />
      ))}
      <text
        x='20'
        y='20'
        textAnchor='middle'
        dominantBaseline='central'
        fontSize={dialSize(value)}
        className='lore-card-dial-text'
      >
        {value}
      </text>
    </svg>
  )
}

function Epochs({ card }: { card: CharacterCard }) {
  if (card.born_epoch === null)
    return (
      <span
        className='lore-card-epochs'
        role='img'
        aria-label={epochLine(card)}
        title={epochLine(card)}
      >
        <Dial value={ENDLESS} />
      </span>
    )
  return (
    <span
      className='lore-card-epochs'
      role='img'
      aria-label={epochLine(card)}
      title={epochLine(card)}
    >
      <Dial value={card.born_epoch} />
      {card.ended_epoch !== null && (
        <>
          <span className='lore-card-epochs-dash' aria-hidden='true' />
          <Dial value={card.ended_epoch} fallen />
        </>
      )}
    </span>
  )
}

function Filigree() {
  return (
    <>
      {CORNERS.map((corner) => (
        <svg
          key={corner}
          viewBox='0 0 48 48'
          className='lore-card-filigree'
          data-corner={corner}
          aria-hidden='true'
        >
          <path d='M3 45 V14 Q3 3 14 3 H45' />
          <path d='M9 45 V18 Q9 9 18 9 H45' />
          <path d='M15 30 Q15 15 30 15' />
          <circle cx='9' cy='9' r='3' />
          <circle cx='24' cy='24' r='1.6' />
        </svg>
      ))}
    </>
  )
}

function Fitted({ className, text }: { className: string; text: string }) {
  const ref = useFitText<HTMLSpanElement>(text)
  return (
    <span ref={ref} className={className} title={text}>
      {text}
    </span>
  )
}

function Head({ card }: { card: CharacterCard }) {
  const rank = rankOf(card)
  const stars = card.stars ?? 0
  return (
    <header className='lore-card-head'>
      {rank && (
        <span
          className='lore-card-rank'
          role='img'
          aria-label={`${rank.label} ${rank.value}`}
          title={`${rank.label} ${rank.value}`}
        >
          {rank.value}
        </span>
      )}
      <span className='lore-card-titles'>
        <Fitted
          className='lore-card-name'
          text={card.fallen ? `† ${card.name}` : card.name}
        />
        {(card.title || stars > 0) && (
          <span className='lore-card-subtitle'>
            {stars > 0 && (
              <span
                className='lore-card-stars'
                role='img'
                aria-label={`${stars} ${stars === 1 ? 'star' : 'stars'}`}
              >
                {Array.from({ length: stars }, (_, index) => (
                  <Star key={index} aria-hidden='true' />
                ))}
              </span>
            )}
            {card.title && (
              <Fitted className='lore-card-epithet' text={card.title} />
            )}
          </span>
        )}
      </span>
    </header>
  )
}

function Band({ card }: { card: CharacterCard }) {
  const { entityType, domain } = useLabels()
  const line = typeLine(card, entityType, domain)
  return (
    <div className='lore-card-band'>
      <Fitted className='lore-card-type' text={line} />
      <Epochs card={card} />
    </div>
  )
}

function MetaIcon({ icon: Icon }: { icon: LucideIcon }) {
  return <Icon aria-hidden='true' />
}

function StatGem({ stat }: { stat: CharacterCardStat }) {
  const full =
    stat.maximum !== null
      ? `${stat.label} ${stat.value} of ${stat.maximum}`
      : `${stat.label} ${stat.value}`
  return (
    <span className='lore-card-slot' title={full}>
      <span className='lore-card-gem' role='img' aria-label={full}>
        <MetaIcon icon={statMeta(stat, false).icon} />
        <span
          className='lore-card-gem-value'
          data-digits={Math.min(String(stat.value).length, 5)}
        >
          {stat.value}
        </span>
      </span>
      <Fitted className='lore-card-slot-label' text={stat.label} />
    </span>
  )
}

function Jewel() {
  return (
    <span className='lore-card-slot' aria-hidden='true'>
      <span className='lore-card-jewel' />
    </span>
  )
}

function Seal({ card }: { card: CharacterCard }) {
  const Icon = FRAME_ICON[frameOf(card)]
  return (
    <span className='lore-card-slot' title={tierLabel(card)}>
      <span className='lore-card-seal'>
        {card.rarity ? (
          <RarityIcon rarity={card.rarity} />
        ) : (
          <Icon aria-hidden='true' />
        )}
      </span>
      <Fitted
        className='lore-card-slot-label lore-card-seal-label'
        text={tierLabel(card)}
      />
    </span>
  )
}

function Foot({ card }: { card: CharacterCard }) {
  const values = footValues(card)
  const slot = (index: number) => {
    const stat = values[index]
    return stat ? <StatGem stat={stat} /> : <Jewel />
  }
  return (
    <footer className='lore-card-foot'>
      {slot(0)}
      {slot(1)}
      <Seal card={card} />
      {slot(2)}
      {slot(3)}
    </footer>
  )
}

function FitText({
  className,
  children,
}: {
  className?: string
  children: ReactNode
}) {
  const ref = useRef<HTMLSpanElement>(null)
  useFitLines(ref)
  return (
    <span ref={ref} className='lore-card-fit'>
      <span className={cn('lore-card-text-block', className)}>{children}</span>
    </span>
  )
}

function Frame({
  card,
  side,
  hidden,
  children,
}: {
  card: CharacterCard
  side: CardSide
  hidden?: boolean
  children: ReactNode
}) {
  const divine = isDivine(card)
  return (
    <div
      className={cn('lore-card', side === 'back' && 'lore-card-back')}
      data-material={materialOf(card)}
      data-divine={divine || undefined}
      aria-hidden={hidden || undefined}
    >
      <div className='lore-card-face'>{children}</div>
      {divine && <Filigree />}
      <span className='lore-card-glare' />
    </div>
  )
}

export function CardFront({ card, artWidth, hidden }: FaceProps) {
  const power = card.abilities[0]
  return (
    <Frame card={card} side='front' hidden={hidden}>
      <Head card={card} />
      <div className='lore-card-media'>
        <div className='lore-card-art'>
          <Picture
            src={mediaUrl(card.cover, artWidth)}
            alt={`Likeness of ${card.name}`}
            fallback={
              <span className='lore-card-sigil'>
                <Sigil seed={card.name} rarity={card.rarity ?? undefined} />
              </span>
            }
          />
          <span className='lore-card-foil' />
          <span className='lore-card-dust' />
        </div>
      </div>
      <Band card={card} />
      <div className='lore-card-text'>
        {power ? (
          <FitText>
            <span className='lore-card-power-name'>{power.name}</span>
            {power.text}
          </FitText>
        ) : (
          <FitText
            className={
              card.flavor ? 'lore-card-flavor' : 'lore-card-text-empty'
            }
          >
            {card.flavor || 'No account of this soul has been written yet.'}
          </FitText>
        )}
      </div>
      <Foot card={card} />
    </Frame>
  )
}

function Bar({ stat }: { stat: CharacterCardStat }) {
  const fill = statFill(stat)
  if (fill === null) return null
  return (
    <span className='lore-card-bar'>
      <span
        className='lore-card-bar-fill'
        ref={(node) => node?.style.setProperty('--fill', String(fill))}
      />
    </span>
  )
}

function Vital({ stat }: { stat: CharacterCardStat }) {
  return (
    <div className='lore-card-vital'>
      <MetaIcon icon={statMeta(stat, false).icon} />
      <span className='lore-card-vital-label'>{stat.label}</span>
      <span className='lore-card-vital-value'>{statText(stat)}</span>
      <Bar stat={stat} />
    </div>
  )
}

function Tile({ stat }: { stat: CharacterCardStat }) {
  const meta = statMeta(stat, false)
  return (
    <div className='lore-card-tile' title={`${stat.label} ${stat.value}`}>
      <span className='lore-card-tile-row'>
        <MetaIcon icon={meta.icon} />
        <span className='lore-card-tile-abbr'>{meta.abbr}</span>
        <span className='lore-card-tile-value'>{stat.value}</span>
      </span>
      <Bar stat={stat} />
    </div>
  )
}

export function CardBack({ card, hidden }: FaceProps) {
  const groups = statGroups(card)
  const vitalStats =
    groups.find((entry) => entry.group === 'Vitals')?.stats ?? []
  const vitals = vitalStats.filter((stat) => statFill(stat) !== null)
  const counts = vitalStats.filter((stat) => statFill(stat) === null)
  const tiles = groups
    .filter((entry) => entry.group !== 'Vitals')
    .flatMap((entry) => entry.stats)
  return (
    <Frame card={card} side='back' hidden={hidden}>
      <Head card={card} />
      <Band card={card} />
      <div className='lore-card-values'>
        {card.stats.length === 0 && (
          <span className='lore-card-text-empty'>No measured values.</span>
        )}
        {vitals.map((stat) => (
          <Vital key={stat.key} stat={stat} />
        ))}
        {counts.length > 0 && (
          <div className='lore-card-tiles' data-columns='2'>
            {counts.map((stat) => (
              <Tile key={stat.key} stat={stat} />
            ))}
          </div>
        )}
        {tiles.length > 0 && (
          <div className='lore-card-tiles'>
            {tiles.map((stat) => (
              <Tile key={stat.key} stat={stat} />
            ))}
          </div>
        )}
      </div>
      <div className='lore-card-lore'>
        {card.abilities.length > 0 && (
          <span className='lore-card-lore-title'>
            <Sparkles aria-hidden='true' />
            Powers
          </span>
        )}
        {card.abilities.map((ability, index) => (
          <span key={`power-${index}`} className='lore-card-text-block'>
            <span className='lore-card-power-name'>{ability.name}</span>
            {ability.text}
          </span>
        ))}
        <span className='lore-card-lore-title'>
          <ScrollText aria-hidden='true' />
          Account
        </span>
        <FitText
          className={card.flavor ? 'lore-card-flavor' : 'lore-card-text-empty'}
        >
          {card.flavor || 'No account of this soul has been written yet.'}
        </FitText>
      </div>
      <Foot card={card} />
    </Frame>
  )
}

type LoreCardProps = Omit<HTMLAttributes<HTMLDivElement>, 'children'> & {
  card: CharacterCard
  flipped?: boolean
  tilt?: boolean
  artWidth?: ThumbnailWidth
}

export function LoreCard({
  card,
  flipped = false,
  tilt = true,
  artWidth = CARD_ART_WIDTH,
  className,
  ...shell
}: LoreCardProps) {
  const tiltRef = useRef<HTMLDivElement>(null)
  const reduced = useReducedMotion()
  const { onPointerMove, onPointerLeave } = useCardTilt(
    tiltRef,
    tilt && !reduced
  )
  return (
    <div
      data-lore-card={card.node_id}
      className={cn('lore-card-shell', className)}
      onPointerMove={onPointerMove}
      onPointerLeave={onPointerLeave}
      {...shell}
    >
      <div ref={tiltRef} className='lore-card-tilt'>
        <div className='lore-card-flip' data-flipped={flipped || undefined}>
          <CardFront card={card} artWidth={artWidth} hidden={flipped} />
          <CardBack card={card} artWidth={artWidth} hidden={!flipped} />
        </div>
      </div>
    </div>
  )
}

export function CardFace({
  card,
  side,
  artWidth,
}: {
  card: CharacterCard
  side: CardSide
  artWidth: ThumbnailWidth
}) {
  return (
    <div className='lore-card-shell'>
      <div className='lore-card-flip'>
        {side === 'front' ? (
          <CardFront card={card} artWidth={artWidth} />
        ) : (
          <CardBack card={card} artWidth={artWidth} />
        )}
      </div>
    </div>
  )
}

import { fnv1a } from '@/lib/hash'
import { RARITIES, type Rarity } from '@/constants/rarity'

type SigilProps = {
  seed: string
  rarity?: Rarity
  label?: string
}

const CENTER = 50
const OUTER = 44
const INNER = 37
const LETTER_SIZE = 38
const LETTER_BASELINE = 63
const NOTCHES = 12
const NOTCH_DEPTH = 4
const RAYS = 16
const RAY_INNER = 46
const RAY_OUTER = 49
const DIAMOND = 4.5
const DEFAULT_TIER = 1
const FALLBACK_LETTER = '?'

function point(angle: number, radius: number): [number, number] {
  return [CENTER + Math.cos(angle) * radius, CENTER + Math.sin(angle) * radius]
}

function initialOf(seed: string): string {
  const letter = Array.from(seed.trim())[0]
  return letter ? letter.toLocaleUpperCase() : FALLBACK_LETTER
}

function Diamonds({
  count,
  radius,
  turn,
}: {
  count: number
  radius: number
  turn: number
}) {
  return (
    <>
      {Array.from({ length: count }, (_, index) => {
        const angle = turn + (index * 2 * Math.PI) / count - Math.PI / 2
        const [x, y] = point(angle, radius)
        return (
          <rect
            key={index}
            x={x - DIAMOND / 2}
            y={y - DIAMOND / 2}
            width={DIAMOND}
            height={DIAMOND}
            transform={`rotate(45 ${x} ${y})`}
            fill='currentColor'
          />
        )
      })}
    </>
  )
}

export function Sigil({ seed, rarity, label }: SigilProps) {
  const tier = rarity ? RARITIES.indexOf(rarity) : DEFAULT_TIER
  const turn = ((fnv1a(seed) % 360) * Math.PI) / 180 / NOTCHES
  return (
    <svg
      data-domain='sigil'
      data-sigil-tier={tier}
      viewBox='0 0 100 100'
      role={label ? 'img' : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
      className='size-full'
    >
      <circle
        cx={CENTER}
        cy={CENTER}
        r={OUTER}
        fill='currentColor'
        fillOpacity={0.1}
        stroke='currentColor'
        strokeWidth={2.5}
      />
      {tier >= 1 && (
        <circle
          cx={CENTER}
          cy={CENTER}
          r={INNER}
          fill='none'
          stroke='currentColor'
          strokeWidth={1.2}
          strokeOpacity={0.6}
        />
      )}
      {tier === 2 && <Diamonds count={4} radius={OUTER} turn={0} />}
      {tier === 3 &&
        Array.from({ length: NOTCHES }, (_, index) => {
          const angle = turn + (index * 2 * Math.PI) / NOTCHES
          const [x1, y1] = point(angle, OUTER)
          const [x2, y2] = point(angle, OUTER - NOTCH_DEPTH)
          return (
            <line
              key={index}
              x1={x1}
              y1={y1}
              x2={x2}
              y2={y2}
              stroke='currentColor'
              strokeWidth={2}
            />
          )
        })}
      {tier === 4 && (
        <>
          <Diamonds count={8} radius={OUTER} turn={0} />
          <path
            d='M38 6 L44 13 L50 4 L56 13 L62 6 L60 16 L40 16 Z'
            fill='currentColor'
          />
        </>
      )}
      {tier >= 5 &&
        Array.from({ length: RAYS }, (_, index) => {
          const angle = (index * 2 * Math.PI) / RAYS
          const [x1, y1] = point(angle, RAY_INNER)
          const [x2, y2] = point(angle, RAY_OUTER + (index % 2 === 0 ? 2 : 0))
          return (
            <line
              key={index}
              x1={x1}
              y1={y1}
              x2={x2}
              y2={y2}
              stroke='currentColor'
              strokeWidth={2}
              strokeLinecap='round'
            />
          )
        })}
      <text
        x={CENTER}
        y={LETTER_BASELINE}
        textAnchor='middle'
        fontSize={LETTER_SIZE}
        fontWeight={700}
        fill='currentColor'
        className='font-display'
      >
        {initialOf(seed)}
      </text>
    </svg>
  )
}

import { useId, useMemo } from 'react'
import { fnv1a, seededRandom } from '@/lib/hash'
import { RARITIES } from '@/constants/rarity'
import { type CharacterCard } from './api'
import { FRAME_ICON, frameOf, materialOf } from './cardModel'
import { lacePath, ticksPath } from './packModel'

const ROLLERS = [7, 10, 11, 13, 14, 15, 17] as const
const OUTER = 36
const DIVINE_JEWELS = { sovereign: 8, obsidian: 4 } as const
const JEWEL_STEP = 0.2
const BEZEL = 21
const PERCENT = 100

function initialOf(name: string): string {
  const letter = Array.from(name.replace(/^†\s*/, '').trim())[0]
  return letter ? letter.toLocaleUpperCase() : '?'
}

function jewelCount(card: CharacterCard): number {
  const material = materialOf(card)
  if (material === 'sovereign' || material === 'obsidian')
    return DIVINE_JEWELS[material]
  return RARITIES.indexOf(material) + 1
}

function jewelAngles(count: number, divine: boolean): number[] {
  if (divine)
    return Array.from(
      { length: count },
      (_, index) => (index / count) * Math.PI * 2 + Math.PI / 2
    )
  const start = Math.PI / 2 - ((count - 1) * JEWEL_STEP) / 2
  return Array.from({ length: count }, (_, index) => start + index * JEWEL_STEP)
}

export function CardEmblem({ card }: { card: CharacterCard }) {
  const id = useId().replace(/:/g, '')
  const Icon = FRAME_ICON[frameOf(card)]
  const material = materialOf(card)
  const divine = material === 'sovereign' || material === 'obsidian'
  const design = useMemo(() => {
    const random = seededRandom(fnv1a(`${card.node_id}:${card.name}`))
    const pick = () => ROLLERS[Math.floor(random() * ROLLERS.length)]
    const outerRoller = pick()
    const innerRoller = pick()
    return {
      lace: lacePath({
        outer: OUTER,
        roller: outerRoller,
        pen: outerRoller * (0.7 + random() * 0.5),
        radius: 47,
        turn: random() * Math.PI,
      }),
      rosette: lacePath({
        outer: OUTER - 6,
        roller: innerRoller,
        pen: innerRoller * (0.55 + random() * 0.4),
        radius: 33,
        turn: random() * Math.PI,
      }),
      x: Math.round(random() * PERCENT),
      y: Math.round(random() * PERCENT),
    }
  }, [card.node_id, card.name])
  const jewels = jewelAngles(jewelCount(card), divine)
  return (
    <span
      className='card-emblem'
      role='img'
      aria-label={`No likeness of ${card.name} yet`}
      ref={(node) => {
        node?.style.setProperty('--emblem-x', `${design.x}%`)
        node?.style.setProperty('--emblem-y', `${design.y}%`)
      }}
    >
      <span className='card-emblem-void' />
      <svg viewBox='0 0 100 100' className='card-emblem-art' aria-hidden='true'>
        <defs>
          <linearGradient
            id={`${id}-metal`}
            x1='0.15'
            y1='0.05'
            x2='0.85'
            y2='0.95'
          >
            <stop offset='0' className='card-emblem-stop-hi' />
            <stop offset='0.32' className='card-emblem-stop-mid' />
            <stop offset='0.55' className='card-emblem-stop-lo' />
            <stop offset='0.78' className='card-emblem-stop-mid' />
            <stop offset='1' className='card-emblem-stop-hi' />
          </linearGradient>
          <linearGradient id={`${id}-letter`} x1='0' y1='0' x2='0' y2='1'>
            <stop offset='0.1' className='card-emblem-stop-hi' />
            <stop offset='0.62' className='card-emblem-stop-mid' />
            <stop offset='1' className='card-emblem-stop-lo' />
          </linearGradient>
          <radialGradient id={`${id}-well`} cx='0.42' cy='0.36' r='0.75'>
            <stop offset='0' className='card-emblem-stop-glow' />
            <stop offset='0.7' className='card-emblem-stop-night' />
          </radialGradient>
          <radialGradient id={`${id}-halo`} cx='0.5' cy='0.5' r='0.5'>
            <stop
              offset='0.55'
              className='card-emblem-stop-accent'
              stopOpacity='0.55'
            />
            <stop
              offset='1'
              className='card-emblem-stop-accent'
              stopOpacity='0'
            />
          </radialGradient>
          <filter
            id={`${id}-soft`}
            x='-20%'
            y='-20%'
            width='140%'
            height='140%'
          >
            <feGaussianBlur stdDeviation='0.9' />
          </filter>
          <filter
            id={`${id}-lift`}
            x='-30%'
            y='-30%'
            width='160%'
            height='160%'
          >
            <feDropShadow
              dx='0'
              dy='0.8'
              stdDeviation='0.9'
              floodOpacity='0.75'
            />
          </filter>
        </defs>
        <g className='card-emblem-lace'>
          <path
            d={design.lace}
            className='card-emblem-line'
            strokeWidth='0.2'
          />
          <circle
            cx='50'
            cy='50'
            r='47.6'
            className='card-emblem-line'
            strokeWidth='0.35'
          />
          <path
            d={ticksPath(120, 44.4, 46.2)}
            className='card-emblem-line'
            strokeWidth='0.25'
          />
        </g>
        <g className='card-emblem-rosette'>
          <path
            d={design.rosette}
            className='card-emblem-line card-emblem-line-bright'
            strokeWidth='0.24'
          />
          <circle
            cx='50'
            cy='50'
            r='34'
            className='card-emblem-line'
            strokeWidth='0.3'
            strokeDasharray='0.6 1.4'
          />
        </g>
        <circle cx='50' cy='50' r='30' fill={`url(#${id}-halo)`} />
        <g filter={`url(#${id}-lift)`}>
          <circle cx='50' cy='50' r={BEZEL + 1.6} fill={`url(#${id}-metal)`} />
          <circle
            cx='50'
            cy='50'
            r={BEZEL + 1.6}
            className='card-emblem-edge'
            strokeWidth='0.35'
          />
          <path
            d={ticksPath(60, BEZEL - 0.6, BEZEL + 1)}
            className='card-emblem-engrave'
            strokeWidth='0.3'
          />
          <circle cx='50' cy='50' r={BEZEL - 1.4} fill={`url(#${id}-well)`} />
          <circle
            cx='50'
            cy='50'
            r={BEZEL - 1.4}
            className='card-emblem-edge'
            strokeWidth='0.45'
          />
          <circle
            cx='50'
            cy='50'
            r={BEZEL - 3.4}
            className='card-emblem-line card-emblem-line-bright'
            strokeWidth='0.25'
          />
          <text
            x='50'
            y='50.6'
            textAnchor='middle'
            dominantBaseline='central'
            className='card-emblem-letter'
            fill={`url(#${id}-letter)`}
          >
            {initialOf(card.name)}
          </text>
          {jewels.map((angle) => {
            const x = 50 + Math.cos(angle) * (BEZEL + 0.2)
            const y = 50 + Math.sin(angle) * (BEZEL + 0.2)
            return (
              <rect
                key={angle}
                x={x - 1.15}
                y={y - 1.15}
                width='2.3'
                height='2.3'
                transform={`rotate(45 ${x} ${y})`}
                className='card-emblem-jewel'
                strokeWidth='0.35'
              />
            )
          })}
          <circle
            cx='50'
            cy={50 - BEZEL - 0.4}
            r='5.4'
            fill={`url(#${id}-metal)`}
          />
          <circle
            cx='50'
            cy={50 - BEZEL - 0.4}
            r='4.1'
            fill={`url(#${id}-well)`}
            className='card-emblem-edge'
            strokeWidth='0.35'
          />
          <Icon
            x={47}
            y={50 - BEZEL - 3.4}
            width={6}
            height={6}
            className='card-emblem-icon'
            strokeWidth={2.2}
          />
        </g>
        <ellipse
          cx='43'
          cy='36'
          rx='10'
          ry='3.6'
          transform='rotate(-32 43 36)'
          className='card-emblem-gleam'
          filter={`url(#${id}-soft)`}
        />
      </svg>
    </span>
  )
}

import { Muted } from '@/components/typography'
import type { GalaxyRecord, StructureRecord } from './api'

const VIEW = 220
const CENTER = VIEW / 2
const TURNS = 48
const ARM_WIND = Math.PI

export type MapStar = { id: number; name: string; x: number; y: number }

function armPath(
  arm: number,
  count: number,
  radius: number,
  scale: number
): string {
  const start = (Math.PI * 2 * arm) / Math.max(count, 1)
  const points: string[] = []
  for (let step = 0; step <= TURNS; step += 1) {
    const reach = step / TURNS
    const angle = start + reach * ARM_WIND
    const length = radius * (0.15 + reach * 0.85) * scale
    points.push(
      `${(CENTER + Math.cos(angle) * length).toFixed(1)},${(CENTER + Math.sin(angle) * length).toFixed(1)}`
    )
  }
  return `M ${points.join(' L ')}`
}

export function GalaxyMap({
  galaxy,
  structures,
  stars,
}: {
  galaxy: GalaxyRecord
  structures: StructureRecord[]
  stars: MapStar[]
}) {
  const scale = (VIEW / 2 - 8) / Math.max(galaxy.radius * 1.3, 1)
  const at = (value: number) => CENTER + value * scale
  return (
    <figure className='flex min-w-0 flex-col items-center gap-2'>
      <svg
        viewBox={`0 0 ${VIEW} ${VIEW}`}
        role='img'
        aria-label={`Map of ${galaxy.name}`}
        className='aspect-square w-full max-w-sm rounded-xl border bg-card'
      >
        <circle
          cx={CENTER}
          cy={CENTER}
          r={galaxy.radius * 1.3 * scale}
          className='fill-none stroke-border'
          strokeDasharray='2 3'
        />
        <circle
          cx={CENTER}
          cy={CENTER}
          r={galaxy.radius * scale}
          className='fill-muted/30 stroke-border'
        />
        {Array.from({ length: galaxy.arm_count }, (_, arm) => (
          <path
            key={arm}
            d={armPath(arm, galaxy.arm_count, galaxy.radius, scale)}
            className='fill-none stroke-primary/40'
            strokeWidth={6}
            strokeLinecap='round'
          />
        ))}
        {structures
          .filter(
            (row) =>
              row.ended_epoch === null &&
              !['spiral_arm', 'halo', 'bulge'].includes(row.kind)
          )
          .map((row) => (
            <circle
              key={row.id}
              cx={at(row.x)}
              cy={at(row.y)}
              r={Math.max(row.radius * scale, 2)}
              className='fill-info/20 stroke-info/60'
            >
              <title>{row.name}</title>
            </circle>
          ))}
        <circle
          cx={CENTER}
          cy={CENTER}
          r={Math.max(galaxy.radius * 0.08 * scale, 2)}
          className='fill-warning/70'
        />
        {stars.map((star) => (
          <circle
            key={star.id}
            cx={at(star.x)}
            cy={at(star.y)}
            r={2.4}
            className='fill-foreground'
          >
            <title>{star.name}</title>
          </circle>
        ))}
      </svg>
      <figcaption>
        <Muted as='span' variant='caption'>
          {`${stars.length} stars · ${structures.filter((row) => row.ended_epoch === null).length} structures`}
        </Muted>
      </figcaption>
    </figure>
  )
}

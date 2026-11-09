import { Orbit } from 'lucide-react'
import { EmptyState, EntityLink } from '@/components/domain'
import { Muted } from '@/components/typography'
import { type StarPhysicsView } from './api'
import { fixed } from './format'

const SIZE = 320
const CENTRE = SIZE / 2
const MARGIN = 26
const STAR_RADIUS = 7
const WORLD_RADIUS = 4
const LABEL_SIZE = 11
const LABEL_OFFSET = 6

export function OrbitView({ view }: { view: StarPhysicsView }) {
  const planets = view.orbits.filter((row) => row.parent_world_id === null)
  const reach = Math.max(
    view.band_outer,
    ...planets.map((row) => row.orbit * (1 + row.eccentricity)),
    0.1
  )
  const scale = (orbit: number) =>
    (CENTRE - MARGIN) * Math.sqrt(Math.max(orbit, 0) / reach)
  if (planets.length === 0)
    return (
      <EmptyState
        icon={Orbit}
        size='inline'
        title='No world circles it'
        description='Hang a world under this star from the Cosmos to see its orbit here.'
      />
    )
  return (
    <figure className='flex min-w-0 flex-col items-center gap-2'>
      <svg
        viewBox={`0 0 ${SIZE} ${SIZE}`}
        role='img'
        aria-label={`Orbits around ${view.name}`}
        className='aspect-square w-full max-w-sm'
      >
        <circle
          cx={CENTRE}
          cy={CENTRE}
          r={scale(view.band_outer)}
          className='fill-success/10 stroke-success/40'
        />
        <circle
          cx={CENTRE}
          cy={CENTRE}
          r={scale(view.band_inner)}
          className='fill-background stroke-success/40'
        />
        {view.giant && (
          <circle
            cx={CENTRE}
            cy={CENTRE}
            r={scale(view.engulf_orbit)}
            className='fill-none stroke-destructive/50'
            strokeDasharray='3 3'
          />
        )}
        <circle
          cx={CENTRE}
          cy={CENTRE}
          r={STAR_RADIUS}
          className='fill-primary'
        />
        {planets.map((row, index) => {
          const width = scale(row.orbit)
          const height =
            width * Math.sqrt(1 - Math.min(row.eccentricity, 0.95) ** 2)
          const shift = width * row.eccentricity
          const angle = (index * 137.5 * Math.PI) / 180
          const x = CENTRE - shift + width * Math.cos(angle)
          const y = CENTRE + height * Math.sin(angle)
          return (
            <g key={row.world_id}>
              <ellipse
                cx={CENTRE - shift}
                cy={CENTRE}
                rx={width}
                ry={height}
                className={
                  row.habitable
                    ? 'fill-none stroke-success'
                    : 'fill-none stroke-muted-foreground/50'
                }
              />
              <circle
                cx={x}
                cy={y}
                r={WORLD_RADIUS}
                className={
                  row.habitable ? 'fill-success' : 'fill-muted-foreground'
                }
              />
              <text
                x={x + LABEL_OFFSET}
                y={y - LABEL_OFFSET}
                className='fill-foreground'
                fontSize={LABEL_SIZE}
              >
                {row.name}
              </text>
            </g>
          )
        })}
      </svg>
      <figcaption className='flex min-w-0 flex-wrap justify-center gap-x-3 gap-y-1'>
        {planets.map((row) => (
          <Muted key={row.world_id} as='span' variant='caption'>
            <EntityLink kind='world' id={String(row.world_id)}>
              {row.name}
            </EntityLink>
            {` · ${fixed(row.orbit)} orbits, ${Math.round(row.eccentricity * 100)}% stretched${row.tidally_locked ? ', one face to the star' : ''}${row.ringed ? ', ringed' : ''}${row.circumbinary ? ', circles both stars' : ''}`}
          </Muted>
        ))}
      </figcaption>
    </figure>
  )
}

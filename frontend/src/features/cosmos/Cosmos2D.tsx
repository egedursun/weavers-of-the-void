import { type KeyboardEvent, useMemo } from 'react'
import { mediaUrl } from '@/features/images/media'
import {
  type CosmosIndex,
  isMisty,
  routeState,
  routeStateText,
} from './model/cosmosModel'
import { STAR_TYPE_LABEL, TRAVEL_METHOD_LABEL } from './model/labels'
import { layoutCosmos2D, curvedPath } from './model/layout2d'
import {
  CLOSED_ROUTE_DASH,
  CLOSED_ROUTE_OPACITY,
  HIDDEN_ROUTE_OPACITY,
  LEGEND_LINE_MAX_WIDTH,
  METHOD_LOOK,
  STAR_LOOK,
  cssVar,
} from './model/looks'

const STAR_GLOW = 30
const STAR_CORE = 15
const WORLD_RADIUS = 11
const MOON_RADIUS = 6
const HIT_RADIUS = 22
const WORLD_COVER_RADIUS = 16
const MOON_COVER_RADIUS = 10
const COVER_WIDTH = 160
const RING_GAP = 7
const LABEL_SIZE = 13
const LABEL_GAP = 18

type Cosmos2DProps = {
  index: CosmosIndex
  selectedWorldId: number | undefined
  selectedStarId: number | undefined
  onSelectWorld: (worldId: number) => void
  onSelectStar: (starId: number) => void
  onDescend: (worldId: number) => void
}

function activate(event: KeyboardEvent, run: () => void) {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    run()
  }
}

export function Cosmos2D({
  index,
  selectedWorldId,
  selectedStarId,
  onSelectWorld,
  onSelectStar,
  onDescend,
}: Cosmos2DProps) {
  const layout = useMemo(() => layoutCosmos2D(index.data), [index])
  const box = layout.viewBox
  return (
    <svg
      role='group'
      aria-label='Cosmos: stars, worlds and routes'
      viewBox={`${box.x} ${box.y} ${box.width} ${box.height}`}
      preserveAspectRatio='xMidYMid meet'
      className='h-full w-full select-none'
    >
      <rect
        x={box.x}
        y={box.y}
        width={box.width}
        height={box.height}
        fill={cssVar('--cosmos-void')}
      />
      {layout.orbits.map((orbit) => (
        <circle
          key={orbit.key}
          cx={orbit.cx}
          cy={orbit.cy}
          r={orbit.r}
          fill='none'
          stroke={cssVar('--cosmos-orbit')}
          strokeDasharray='3 5'
        />
      ))}
      {index.data.routes.map((route) => {
        const from = layout.worlds.get(route.world_a_id)
        const to = layout.worlds.get(route.world_b_id)
        if (!from || !to) return null
        const look = METHOD_LOOK[route.method]
        const open = routeState(route).open
        const dash = open ? look.dash : CLOSED_ROUTE_DASH
        return (
          <path
            key={route.id}
            d={curvedPath(from, to, look.curve)}
            fill='none'
            stroke={cssVar(look.token)}
            strokeWidth={Math.min(look.width, LEGEND_LINE_MAX_WIDTH)}
            strokeDasharray={dash.length ? dash.join(' ') : undefined}
            strokeLinecap='round'
            opacity={
              !open
                ? CLOSED_ROUTE_OPACITY
                : !route.known
                  ? HIDDEN_ROUTE_OPACITY
                  : look.opacity
            }
          >
            <title>
              {`${TRAVEL_METHOD_LABEL[route.method]}${route.known ? '' : ' · a hidden route the mortals do not know'} · ${routeStateText(route)}${route.description ? ` · ${route.description}` : ''}`}
            </title>
          </path>
        )
      })}
      {index.data.stars.map((star) => {
        const point = layout.stars.get(star.id)
        if (!point) return null
        const look = STAR_LOOK[star.star_type]
        const selected = star.id === selectedStarId
        return (
          <g
            key={star.id}
            role='button'
            tabIndex={0}
            aria-label={`${star.name}, ${STAR_TYPE_LABEL[star.star_type]}`}
            aria-pressed={selected}
            className='cursor-pointer'
            onClick={() => onSelectStar(star.id)}
            onKeyDown={(event) => activate(event, () => onSelectStar(star.id))}
          >
            <circle
              cx={point.x}
              cy={point.y}
              r={STAR_GLOW}
              fill={cssVar(look.token)}
              opacity={0.12}
            />
            {star.cover ? (
              <>
                <clipPath id={`cosmos-star-${star.id}`}>
                  <circle cx={point.x} cy={point.y} r={STAR_CORE} />
                </clipPath>
                <image
                  href={mediaUrl(star.cover, COVER_WIDTH) ?? undefined}
                  x={point.x - STAR_CORE}
                  y={point.y - STAR_CORE}
                  width={STAR_CORE * 2}
                  height={STAR_CORE * 2}
                  preserveAspectRatio='xMidYMid slice'
                  clipPath={`url(#cosmos-star-${star.id})`}
                />
                <circle
                  cx={point.x}
                  cy={point.y}
                  r={STAR_CORE}
                  fill='none'
                  stroke={
                    selected ? cssVar('--cosmos-copper') : cssVar(look.token)
                  }
                  strokeWidth={2}
                />
              </>
            ) : (
              <circle
                cx={point.x}
                cy={point.y}
                r={STAR_CORE}
                fill={cssVar(look.token)}
                stroke={selected ? cssVar('--cosmos-copper') : 'none'}
                strokeWidth={2}
              />
            )}
            <text
              x={point.x}
              y={point.y + STAR_GLOW + LABEL_SIZE}
              textAnchor='middle'
              fontSize={LABEL_SIZE}
              fill={cssVar('--cosmos-label')}
            >
              {star.name}
            </text>
          </g>
        )
      })}
      {index.worlds.map((item) => {
        const point = layout.worlds.get(item.world.id)
        if (!point) return null
        const moon = item.world.parent_world_id !== null
        const radius = item.cover
          ? moon
            ? MOON_COVER_RADIUS
            : WORLD_COVER_RADIUS
          : moon
            ? MOON_RADIUS
            : WORLD_RADIUS
        const selected = item.world.id === selectedWorldId
        const misty = isMisty(item)
        const fill =
          index.palette(item.world.world_type)[4] ?? cssVar('--cosmos-fog')
        return (
          <g
            key={item.world.id}
            role='button'
            tabIndex={0}
            aria-label={`${item.world.name}, ${item.type_label}${misty ? ', in mist' : ''}`}
            aria-pressed={selected}
            data-world-id={item.world.id}
            className='cursor-pointer'
            onClick={() => onSelectWorld(item.world.id)}
            onDoubleClick={() => onDescend(item.world.id)}
            onKeyDown={(event) =>
              activate(event, () =>
                selected && event.key === 'Enter'
                  ? onDescend(item.world.id)
                  : onSelectWorld(item.world.id)
              )
            }
          >
            <circle
              cx={point.x}
              cy={point.y}
              r={HIT_RADIUS}
              fill='transparent'
            />
            {selected && (
              <circle
                cx={point.x}
                cy={point.y}
                r={radius + RING_GAP}
                fill='none'
                stroke={cssVar('--cosmos-copper')}
                strokeWidth={2}
              />
            )}
            {item.cover && (
              <>
                <clipPath id={`cosmos-world-${item.world.id}`}>
                  <circle cx={point.x} cy={point.y} r={radius} />
                </clipPath>
                <image
                  href={mediaUrl(item.cover, COVER_WIDTH) ?? undefined}
                  x={point.x - radius}
                  y={point.y - radius}
                  width={radius * 2}
                  height={radius * 2}
                  preserveAspectRatio='xMidYMid slice'
                  clipPath={`url(#cosmos-world-${item.world.id})`}
                  opacity={misty ? 0.45 : 1}
                />
              </>
            )}
            <circle
              cx={point.x}
              cy={point.y}
              r={radius}
              fill={item.cover ? 'none' : fill}
              stroke={item.cover ? fill : cssVar('--cosmos-void')}
              strokeWidth={item.cover ? 2 : 1.5}
              opacity={misty ? 0.45 : 1}
              strokeDasharray={
                item.world.discovery === 'legend' ? '2 2' : undefined
              }
            />
            <text
              x={point.x}
              y={point.y + radius + LABEL_GAP}
              textAnchor='middle'
              fontSize={moon ? LABEL_SIZE - 2 : LABEL_SIZE}
              fill={cssVar(misty ? '--cosmos-label-muted' : '--cosmos-label')}
              fontStyle={misty ? 'italic' : undefined}
            >
              {item.world.name}
            </text>
          </g>
        )
      })}
    </svg>
  )
}

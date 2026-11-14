import { type ReactNode, useId } from 'react'
import { agree, plural } from '@/lib/units'
import { cn } from '@/lib/utils'
import { type LandPick } from './LandScene3D'
import { type LandScene } from './api'
import { type Cell, hexToWorld, waterDirection } from './hex'
import {
  COVERS,
  COVER_FILL,
  COVER_TEXTURE,
  GROUNDS,
  GROUND_FILL,
  GROUND_RELIEF,
  type LandTexture,
} from './labels'

const RADIUS = 1.15
const CORNERS = Array.from({ length: 6 }, (_, index) => {
  const angle = (Math.PI / 3) * index + Math.PI / 6
  return [Math.cos(angle) * RADIUS, Math.sin(angle) * RADIUS] as const
})
const PAD = 2
const SIDES = 6
const NAME_SIZE = 0.62
const CHAR = 0.62
const TEXTURE_SIZE = 0.9

type Point = readonly [number, number]
type Tile = LandScene['tiles'][number]
type MarkKind = 'settlement' | 'place' | 'work' | 'resource'
type Mark = {
  kind: MarkKind
  id: number
  q: number
  r: number
  text: string
  name: string
  size: number
  standing: boolean
}

function hexPoints(x: number, z: number): string {
  return CORNERS.map(([dx, dz]) => `${x + dx},${z + dz}`).join(' ')
}

function key(q: number, r: number): string {
  return `${q},${r}`
}

function neighbours(tile: Cell): Cell[] {
  return Array.from({ length: SIDES }, (_, side) => {
    const [dq, dr] = waterDirection(side)
    return [tile[0] + dq, tile[1] + dr] as const
  })
}

function sharedEdge(from: Point, to: Point): [Point, Point] {
  const corners = CORNERS.map(
    ([dx, dz]) => [from[0] + dx, from[1] + dz] as const
  )
  const [first, second] = [...corners].sort(
    (a, b) =>
      Math.hypot(a[0] - to[0], a[1] - to[1]) -
      Math.hypot(b[0] - to[0], b[1] - to[1])
  )
  return [first, second]
}

function midpoint([a, b]: [Point, Point]): Point {
  return [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2]
}

function waterways(tiles: Tile[]) {
  const byKey = new Map(tiles.map((tile) => [key(tile.q, tile.r), tile]))
  const rivers: [Point, Point][] = []
  const springs: Point[] = []
  const coasts: [Point, Point][] = []
  const seen = new Set<string>()
  for (const tile of tiles) {
    const centre = hexToWorld(tile.q, tile.r)
    let joined = false
    for (const [q, r] of neighbours([tile.q, tile.r])) {
      const other = byKey.get(key(q, r))
      if (!other) continue
      const there = hexToWorld(q, r)
      if (tile.ground !== 'water' && other.ground === 'water')
        coasts.push(sharedEdge(centre, there))
      if (!tile.river) continue
      if (other.river) {
        joined = true
        const pair = [key(tile.q, tile.r), key(q, r)].sort().join('|')
        if (!seen.has(pair)) {
          seen.add(pair)
          rivers.push([centre, there])
        }
      } else if (other.ground === 'water' && tile.ground !== 'water') {
        joined = true
        rivers.push([centre, midpoint(sharedEdge(centre, there))])
      }
    }
    if (tile.river && !joined && tile.ground !== 'water') springs.push(centre)
  }
  return { rivers, springs, coasts }
}

function marksOf(scene: LandScene): Mark[] {
  return [
    ...scene.resources.map((item) => ({
      kind: 'resource' as const,
      id: item.node.id,
      q: item.q,
      r: item.r,
      text: `${item.node.name}: richness ${item.richness}, ${item.reserve} of ${item.initial_reserve} left`,
      name: item.node.name,
      size: 0.22 + (item.richness / 100) * 0.2,
      standing: item.reserve > 0,
    })),
    ...scene.works.map((item) => ({
      kind: 'work' as const,
      id: item.node.id,
      q: item.q,
      r: item.r,
      text: `${item.node.name}: level ${item.level}, ${item.state}`,
      name: item.node.name,
      size: 0.34,
      standing: item.state === 'complete',
    })),
    ...scene.places.map((item) => ({
      kind: 'place' as const,
      id: item.node.id,
      q: item.q,
      r: item.r,
      text: `${item.node.name}: ${item.detail.replaceAll('_', ' ')}`,
      name: item.node.name,
      size: 0.36,
      standing: true,
    })),
    ...scene.settlements.map((item) => ({
      kind: 'settlement' as const,
      id: item.node.id,
      q: item.q,
      r: item.r,
      text: `${item.node.name}: ${item.detail} ${agree(Number(item.detail), 'person', 'people')}`,
      name: item.node.name,
      size: 0.46,
      standing: true,
    })),
  ]
}

type Box = readonly [number, number, number, number]

function overlaps(box: Box, taken: Box[]): boolean {
  return taken.some(
    (other) =>
      box[0] < other[2] &&
      other[0] < box[2] &&
      box[1] < other[3] &&
      other[1] < box[3]
  )
}

function labelsOf(
  marks: Mark[]
): { id: number; x: number; y: number; text: string }[] {
  const taken: Box[] = []
  return marks
    .filter((mark) => mark.kind === 'settlement')
    .flatMap((mark) => {
      const [x, z] = hexToWorld(mark.q, mark.r)
      const half = (mark.name.length * NAME_SIZE * CHAR) / 2
      const below = z + mark.size + NAME_SIZE + 0.15
      const above = z - mark.size - 0.35
      const spot = [below, above]
        .map((y) => ({
          y,
          box: [x - half, y - NAME_SIZE, x + half, y + NAME_SIZE * 0.3] as Box,
        }))
        .find((option) => !overlaps(option.box, taken))
      if (!spot) return []
      taken.push(spot.box)
      return [{ id: mark.id, x, y: spot.y, text: mark.name }]
    })
}

function Textures({ prefix }: { prefix: string }) {
  const size = TEXTURE_SIZE
  const half = size / 2
  const textures: Record<LandTexture, ReactNode> = {
    trees: (
      <>
        <circle
          cx={half / 2}
          cy={half / 2}
          r={0.15}
          className='fill-black/25'
        />
        <circle
          cx={half * 1.5}
          cy={half * 1.5}
          r={0.15}
          className='fill-black/25'
        />
      </>
    ),
    furrows: (
      <path
        d={`M0,${size} L${size},0 M${-half},${half} L${half},${-half} M${half},${size + half} L${size + half},${half}`}
        className='stroke-black/20'
        strokeWidth={0.07}
      />
    ),
    grass: (
      <>
        <circle cx={half / 2} cy={half} r={0.06} className='fill-black/20' />
        <circle
          cx={half * 1.5}
          cy={half / 3}
          r={0.06}
          className='fill-black/20'
        />
      </>
    ),
    reeds: (
      <path
        d={`M${half / 3},${half} h${half / 1.5} M${half * 1.2},${size * 0.85} h${half / 1.5}`}
        className='stroke-black/25'
        strokeWidth={0.06}
        strokeLinecap='round'
      />
    ),
    stubble: <circle cx={half} cy={half} r={0.05} className='fill-black/20' />,
    blocks: (
      <>
        <rect
          x={0.08}
          y={0.08}
          width={0.28}
          height={0.28}
          rx={0.04}
          className='fill-black/25'
        />
        <rect
          x={half + 0.06}
          y={half + 0.06}
          width={0.28}
          height={0.28}
          rx={0.04}
          className='fill-black/25'
        />
      </>
    ),
    spoil: (
      <path
        d={`M0,0 L${size},${size} M${size},0 L0,${size}`}
        className='stroke-black/30'
        strokeWidth={0.07}
      />
    ),
    ridges: (
      <path
        d={`M${half / 2},${half * 1.2} l${half / 2},${-half / 1.6} l${half / 2},${half / 1.6}`}
        className='fill-none stroke-black/25'
        strokeWidth={0.07}
        strokeLinejoin='round'
      />
    ),
    snow: (
      <path
        d={`M${half / 2},${half * 1.2} l${half / 2},${-half / 1.6} l${half / 2},${half / 1.6}`}
        className='fill-none stroke-black/15'
        strokeWidth={0.06}
        strokeLinejoin='round'
      />
    ),
    swell: (
      <path
        d={`M0,${half} q${size / 4},${-0.12} ${half},0 t${half},0`}
        className='fill-none stroke-white/25'
        strokeWidth={0.06}
      />
    ),
  }
  return (
    <defs>
      {(Object.keys(textures) as LandTexture[]).map((name) => (
        <pattern
          key={name}
          id={`${prefix}-${name}`}
          width={size}
          height={size}
          patternUnits='userSpaceOnUse'
        >
          {textures[name]}
        </pattern>
      ))}
    </defs>
  )
}

function MarkShape({
  mark,
  chosen,
  x,
  z,
}: {
  mark: Mark
  chosen: boolean
  x: number
  z: number
}) {
  const ring = chosen ? 'stroke-primary' : 'stroke-background'
  const width = chosen ? 0.16 : 0.08
  if (mark.kind === 'settlement')
    return (
      <>
        <circle
          cx={x}
          cy={z}
          r={mark.size + 0.14}
          className={cn(
            'fill-card',
            chosen ? 'stroke-primary' : 'stroke-foreground'
          )}
          strokeWidth={width}
        />
        <circle
          cx={x}
          cy={z}
          r={mark.size * 0.55}
          className='fill-brand-gold'
        />
      </>
    )
  if (mark.kind === 'place')
    return (
      <polygon
        points={`${x},${z - mark.size} ${x + mark.size},${z} ${x},${z + mark.size} ${x - mark.size},${z}`}
        className={cn('fill-tincture-purple', ring)}
        strokeWidth={width}
      />
    )
  if (mark.kind === 'work')
    return (
      <rect
        x={x - mark.size}
        y={z - mark.size}
        width={mark.size * 2}
        height={mark.size * 2}
        rx={0.1}
        className={cn(
          mark.standing ? 'fill-tincture-brown' : 'fill-muted-foreground',
          ring
        )}
        strokeWidth={width}
      />
    )
  return (
    <circle
      cx={x}
      cy={z}
      r={mark.size}
      className={cn(
        mark.standing ? 'fill-tincture-celeste' : 'fill-muted-foreground',
        ring
      )}
      strokeWidth={width}
    />
  )
}

export function LandPlan2D({
  scene,
  selected,
  onPick,
  fill = false,
}: {
  scene: LandScene
  selected: LandPick
  onPick: (pick: LandPick) => void
  fill?: boolean
}) {
  const prefix = `land${useId().replaceAll(':', '')}`
  const points = scene.tiles.map((tile) => hexToWorld(tile.q, tile.r))
  const xs = points.map(([x]) => x)
  const zs = points.map(([, z]) => z)
  const box = [
    Math.min(0, ...xs) - PAD,
    Math.min(0, ...zs) - PAD,
    Math.max(0, ...xs) - Math.min(0, ...xs) + PAD * 2,
    Math.max(0, ...zs) - Math.min(0, ...zs) + PAD * 2,
  ]
  const { rivers, springs, coasts } = waterways(scene.tiles)
  const marks = marksOf(scene)
  const names = labelsOf(marks)
  return (
    <svg
      viewBox={box.join(' ')}
      role='img'
      aria-label={`Land of ${scene.region.name}: ${plural(scene.tiles.length, 'tile', 'tiles')}, ${plural(scene.settlements.length, 'settlement', 'settlements')}, ${plural(scene.resources.length, 'deposit', 'deposits')}`}
      className={fill ? 'block h-full w-full' : 'block h-auto w-full'}
    >
      <Textures prefix={prefix} />
      {scene.tiles.map((tile) => {
        const [x, z] = hexToWorld(tile.q, tile.r)
        const chosen =
          selected?.kind === 'tile' &&
          selected.q === tile.q &&
          selected.r === tile.r
        const texture =
          tile.cover === 'open'
            ? GROUND_RELIEF[tile.ground]
            : COVER_TEXTURE[tile.cover]
        return (
          <g
            key={`tile-${tile.q}-${tile.r}`}
            className='cursor-pointer'
            onClick={() => onPick({ kind: 'tile', q: tile.q, r: tile.r })}
          >
            <title>{`${GROUNDS[tile.ground]}, ${COVERS[tile.cover]}${tile.river ? ', river' : ''}`}</title>
            <polygon
              points={hexPoints(x, z)}
              className={cn(
                tile.cover === 'open'
                  ? GROUND_FILL[tile.ground]
                  : COVER_FILL[tile.cover],
                'stroke-land-line'
              )}
              strokeWidth={0.05}
            />
            {texture && (
              <polygon
                points={hexPoints(x, z)}
                fill={`url(#${prefix}-${texture})`}
                className='pointer-events-none'
              />
            )}
            {chosen && (
              <polygon
                points={hexPoints(x, z)}
                className='pointer-events-none fill-none stroke-primary'
                strokeWidth={0.18}
              />
            )}
          </g>
        )
      })}
      <g className='pointer-events-none'>
        {coasts.map(([a, b], index) => (
          <line
            key={`coast-${index}`}
            x1={a[0]}
            y1={a[1]}
            x2={b[0]}
            y2={b[1]}
            className='stroke-land-shore'
            strokeWidth={0.2}
            strokeLinecap='round'
          />
        ))}
        {rivers.map(([a, b], index) => (
          <line
            key={`river-${index}`}
            x1={a[0]}
            y1={a[1]}
            x2={b[0]}
            y2={b[1]}
            className='stroke-land-river'
            strokeWidth={0.34}
            strokeLinecap='round'
          />
        ))}
        {springs.map(([x, z], index) => (
          <circle
            key={`spring-${index}`}
            cx={x}
            cy={z}
            r={0.24}
            className='fill-land-river'
          />
        ))}
      </g>
      {marks.map((mark) => {
        const [x, z] = hexToWorld(mark.q, mark.r)
        const chosen =
          selected !== null &&
          selected.kind === mark.kind &&
          'id' in selected &&
          selected.id === mark.id
        return (
          <g
            key={`${mark.kind}-${mark.id}`}
            className='cursor-pointer'
            onClick={() => onPick({ kind: mark.kind, id: mark.id })}
          >
            <title>{mark.text}</title>
            <MarkShape mark={mark} chosen={chosen} x={x} z={z} />
          </g>
        )
      })}
      {names.map((name) => (
        <text
          key={`name-${name.id}`}
          x={name.x}
          y={name.y}
          textAnchor='middle'
          fontSize={NAME_SIZE}
          fontWeight={600}
          className='pointer-events-none fill-foreground stroke-background'
          strokeWidth={0.18}
          paintOrder='stroke'
        >
          {name.text}
        </text>
      ))}
    </svg>
  )
}

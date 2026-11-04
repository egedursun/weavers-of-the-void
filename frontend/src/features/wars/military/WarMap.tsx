import { useEffect, useMemo, useRef, useState } from 'react'
import { Link } from '@tanstack/react-router'
import { Castle, Flag, Map as MapIcon, Swords, Users } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { EmptyState, EpochSlider, IconStat } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { type MapView, useWorldMap } from '@/features/map/api'
import { buildTerrain, drawTexture } from '@/features/map/terrainLayer'
import type { ArmyCard, WarRoom } from './api'
import { nameOf } from './depth'
import { STANCE } from './labels'
import { Panel, Tag } from './parts'

const SIDE_FILL = [
  'fill-destructive',
  'fill-info',
  'fill-warning',
  'fill-success',
]
const SIDE_STROKE = [
  'stroke-destructive',
  'stroke-info',
  'stroke-warning',
  'stroke-success',
]
const SIDE_SWATCH = ['bg-destructive', 'bg-info', 'bg-warning', 'bg-success']
const CANVAS_WIDTH = 960
const PAD = 0.18
const MIN_SPAN = 0.22
const UNIT_DIVISOR = 320

type Point = { x: number; y: number }
type Box = { x: number; y: number; width: number; height: number }

function placeOf(
  army: ArmyCard,
  epoch: number
): { region: number | null; stance: string } {
  const last = army.movements.filter((move) => move.epoch <= epoch).at(-1)
  return last
    ? { region: last.to_region?.id ?? null, stance: last.stance }
    : { region: army.region?.id ?? null, stance: army.stance }
}

function positions(view: MapView): {
  regions: Map<number, Point>
  points: Map<number, Point>
} {
  const regions = new Map<number, Point>()
  view.geometry.regions.forEach((region) => {
    const at = region.centroid ?? region.anchor
    if (at) regions.set(region.id, { x: at[0], y: at[1] })
  })
  const points = new Map<number, Point>()
  view.points.forEach((point) => {
    if (point.x !== null && point.y !== null)
      points.set(point.entity.id, { x: point.x, y: point.y })
  })
  return { regions, points }
}

function frame(view: MapView, spots: Point[]): Box {
  const whole = view.geometry.window
  if (spots.length === 0) return whole
  const xs = spots.map((spot) => spot.x)
  const ys = spots.map((spot) => spot.y)
  const span = Math.max(
    Math.max(...xs) - Math.min(...xs),
    Math.max(...ys) - Math.min(...ys),
    whole.width * MIN_SPAN
  )
  const side = span * (1 + PAD * 2)
  const cx = (Math.max(...xs) + Math.min(...xs)) / 2
  const cy = (Math.max(...ys) + Math.min(...ys)) / 2
  const width = Math.min(whole.width, side)
  const height = Math.min(whole.height, side * (whole.height / whole.width))
  const x = Math.min(
    Math.max(whole.x, cx - width / 2),
    whole.x + whole.width - width
  )
  const y = Math.min(
    Math.max(whole.y, cy - height / 2),
    whole.y + whole.height - height
  )
  return { x, y, width, height }
}

function Terrain({ view, box }: { view: MapView; box: Box }) {
  const canvas = useRef<HTMLCanvasElement>(null)
  const texture = useMemo(() => buildTerrain(view.geometry), [view.geometry])
  useEffect(() => {
    const element = canvas.current
    const context = element?.getContext('2d')
    if (!element || !context || !texture) return
    const scale = CANVAS_WIDTH / box.width
    context.setTransform(scale, 0, 0, scale, -box.x * scale, -box.y * scale)
    drawTexture(context, view.geometry, texture)
  }, [box, texture, view.geometry])
  return (
    <canvas
      ref={canvas}
      aria-hidden='true'
      width={CANVAS_WIDTH}
      height={Math.round((CANVAS_WIDTH * box.height) / box.width)}
      className='block h-auto w-full'
    />
  )
}

function Legend({
  sides,
  room,
  epoch,
  where,
}: {
  sides: { id: number; name: string }[]
  room: WarRoom
  epoch: number
  where: Map<number, string>
}) {
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <div className='flex min-w-0 flex-wrap gap-x-3 gap-y-1'>
        {sides.map((side, index) => (
          <span key={side.id} className='flex min-w-0 items-center gap-1.5'>
            <span
              aria-hidden='true'
              className={`size-icon-xs shrink-0 rounded-full ${SIDE_SWATCH[index % SIDE_SWATCH.length]}`}
            />
            <Text as='span' variant='caption' truncate>
              {side.name}
            </Text>
          </span>
        ))}
      </div>
      <ul className='flex min-w-0 flex-col gap-1.5'>
        {room.armies.map((army, index) => {
          const place = placeOf(army, epoch)
          return (
            <li
              key={army.army?.id ?? index}
              className='flex min-w-0 flex-wrap items-center gap-1.5 rounded-lg border bg-background px-2.5 py-1.5'
            >
              <Text
                as='span'
                weight='medium'
                truncate
                className='min-w-0 flex-1'
              >
                {army.army?.name ?? 'An army'}
              </Text>
              <Tag item={nameOf(STANCE, place.stance)} />
              <Muted as='span' variant='caption'>
                {place.region !== null
                  ? (where.get(place.region) ?? 'beyond the known map')
                  : 'off the map'}
              </Muted>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

export function WarMap({ room }: { room: WarRoom }) {
  const map = useWorldMap(room.war.world_id, null)
  const epochs = useMemo(() => {
    const seen = new Set<number>([room.war.started_epoch])
    room.armies.forEach((army) =>
      army.movements.forEach((move) => seen.add(move.epoch))
    )
    room.fronts.forEach((front) => seen.add(front.since_epoch))
    room.battles.forEach((battle) => seen.add(battle.epoch))
    room.sieges.forEach((siege) => seen.add(siege.started_epoch))
    return [...seen].sort((first, second) => first - second)
  }, [room])
  const [picked, setPicked] = useState<number | null>(null)
  const epoch = picked ?? epochs.at(-1) ?? room.war.started_epoch
  const sides = useMemo(() => {
    const found = new Map<number, string>()
    room.war.sides.forEach((side) => {
      if (side.entity) found.set(side.entity.id, side.entity.name)
    })
    room.armies.forEach((army) => {
      if (army.owner && !found.has(army.owner.id))
        found.set(army.owner.id, army.owner.name)
    })
    return [...found.entries()].map(([id, name]) => ({ id, name }))
  }, [room])
  const names = useMemo(() => {
    const found = new Map<number, string>()
    const note = (ref: { id: number; name: string } | null | undefined) => {
      if (ref) found.set(ref.id, ref.name)
    }
    room.armies.forEach((army) => {
      note(army.region)
      army.movements.forEach((move) => {
        note(move.from_region)
        note(move.to_region)
      })
    })
    room.fronts.forEach((front) => {
      note(front.first_region)
      note(front.second_region)
    })
    room.occupations.forEach((occupation) => note(occupation.region))
    room.battles.forEach((battle) => note(battle.place))
    return found
  }, [room])
  const view = map.data
  const located = useMemo(() => (view ? positions(view) : null), [view])
  const box = useMemo(() => {
    if (!view || !located) return null
    const spots = [...names.keys()]
      .map((id) => located.regions.get(id) ?? located.points.get(id))
      .filter((spot): spot is Point => spot !== undefined)
    room.sieges.forEach((siege) => {
      const spot = siege.besieged
        ? located.points.get(siege.besieged.id)
        : undefined
      if (spot) spots.push(spot)
    })
    return frame(view, spots)
  }, [located, names, room.sieges, view])
  const side = (id: number | undefined) =>
    Math.max(
      0,
      sides.findIndex((entry) => entry.id === id)
    )
  const header = (
    <Button asChild size='sm' variant='outline'>
      <Link to='/map' search={{ world: room.war.world_id }}>
        <MapIcon />
        World map
      </Link>
    </Button>
  )
  if (!view || !located || !box) {
    return (
      <Panel title='War map' icon={MapIcon} tone='verdigris' actions={header}>
        <EmptyState
          icon={MapIcon}
          title={
            map.isLoading ? 'Unrolling the map' : 'No map of this world yet'
          }
          description='Fronts, marches and sieges are drawn on the world map once it is surveyed.'
        />
      </Panel>
    )
  }
  const unit = box.width / UNIT_DIVISOR
  const at = (id: number | undefined | null) =>
    id === undefined || id === null
      ? undefined
      : (located.regions.get(id) ?? located.points.get(id))
  const fronts = room.fronts.filter((front) => front.since_epoch <= epoch)
  const sieges = room.sieges.filter(
    (siege) =>
      siege.started_epoch <= epoch &&
      (siege.ended_epoch === null || siege.ended_epoch >= epoch)
  )
  const battles = room.battles.filter((battle) => battle.epoch <= epoch)
  const occupied = room.occupations.filter(
    (occupation) => occupation.since_epoch <= epoch
  )
  const labelled = [...names.entries()]
    .map(([id, name]) => ({ id, name, spot: at(id) }))
    .filter((entry) => entry.spot !== undefined)
  return (
    <Panel
      title='War map'
      icon={MapIcon}
      tone='verdigris'
      hint='Fronts, marches, battles and sieges on the land itself'
      actions={header}
    >
      <div
        data-surface='WarMap'
        className='grid min-w-0 grid-cols-1 gap-3 @3xl/mil:grid-cols-5'
      >
        <div className='relative min-w-0 self-start overflow-hidden rounded-lg border bg-background @3xl/mil:col-span-3'>
          <Terrain view={view} box={box} />
          <svg
            viewBox={`${box.x} ${box.y} ${box.width} ${box.height}`}
            role='img'
            aria-label={`War map at epoch ${epoch}`}
            className='absolute inset-0 size-full'
          >
            {occupied.map((occupation, index) => {
              const spot = at(occupation.region?.id)
              if (!spot) return null
              return (
                <circle
                  key={`occupation.${occupation.region?.id ?? index}`}
                  cx={spot.x}
                  cy={spot.y}
                  r={unit * 16}
                  className={`${SIDE_STROKE[side(occupation.occupier?.id) % SIDE_STROKE.length]} fill-none`}
                  strokeWidth={unit * 2}
                  strokeDasharray={`${unit * 3} ${unit * 3}`}
                  opacity={0.8}
                />
              )
            })}
            {fronts.map((front) => {
              const first = at(front.first_region?.id)
              const second = at(front.second_region?.id)
              if (!first || !second) return null
              return (
                <line
                  key={`${front.first_region?.id}.${front.second_region?.id}`}
                  x1={first.x}
                  y1={first.y}
                  x2={second.x}
                  y2={second.y}
                  className='stroke-destructive'
                  strokeWidth={unit * 3}
                  strokeDasharray={`${unit * 6} ${unit * 4}`}
                  strokeLinecap='round'
                />
              )
            })}
            {room.armies.map((army, index) => {
              const trail = army.movements
                .filter((move) => move.epoch <= epoch)
                .flatMap((move) => [
                  at(move.from_region?.id),
                  at(move.to_region?.id),
                ])
                .filter((spot): spot is Point => spot !== undefined)
              if (trail.length < 2) return null
              return (
                <polyline
                  key={`trail.${army.army?.id ?? index}`}
                  points={trail.map((spot) => `${spot.x},${spot.y}`).join(' ')}
                  className={`${SIDE_STROKE[side(army.owner?.id) % SIDE_STROKE.length]} fill-none`}
                  strokeWidth={unit * 2}
                  strokeLinejoin='round'
                  strokeLinecap='round'
                  opacity={0.75}
                />
              )
            })}
            {labelled.map((entry) => (
              <g key={`label.${entry.id}`}>
                <circle
                  cx={entry.spot!.x}
                  cy={entry.spot!.y}
                  r={unit * 3}
                  className='fill-background stroke-foreground'
                  strokeWidth={unit}
                />
                <text
                  x={entry.spot!.x}
                  y={entry.spot!.y - unit * 7}
                  textAnchor='middle'
                  className='fill-foreground stroke-background'
                  strokeWidth={unit * 2.5}
                  paintOrder='stroke'
                  fontSize={unit * 10}
                  fontWeight={600}
                >
                  {entry.name}
                </text>
              </g>
            ))}
            {battles.map((battle) => {
              const spot = at(battle.place?.id)
              if (!spot) return null
              const size = unit * 5
              return (
                <g
                  key={`battle.${battle.id}`}
                  className='stroke-destructive'
                  strokeWidth={unit * 2}
                  strokeLinecap='round'
                >
                  <title>{`Battle, epoch ${battle.epoch}`}</title>
                  <line
                    x1={spot.x - size}
                    y1={spot.y + unit * 9 - size}
                    x2={spot.x + size}
                    y2={spot.y + unit * 9 + size}
                  />
                  <line
                    x1={spot.x - size}
                    y1={spot.y + unit * 9 + size}
                    x2={spot.x + size}
                    y2={spot.y + unit * 9 - size}
                  />
                </g>
              )
            })}
            {sieges.map((siege) => {
              const spot = siege.besieged ? at(siege.besieged.id) : undefined
              if (!spot) return null
              const size = unit * 7
              return (
                <g key={`siege.${siege.id}`}>
                  <title>{`Siege of ${siege.besieged?.name ?? 'a city'}`}</title>
                  <rect
                    x={spot.x - size}
                    y={spot.y - size}
                    width={size * 2}
                    height={size * 2}
                    rx={unit * 2}
                    className={`${SIDE_FILL[side(siege.besieger?.id) % SIDE_FILL.length]} stroke-background`}
                    strokeWidth={unit * 1.5}
                  />
                  <circle
                    cx={spot.x}
                    cy={spot.y}
                    r={size * 1.8}
                    className='fill-none stroke-warning'
                    strokeWidth={unit * 1.5}
                    strokeDasharray={`${unit * 2} ${unit * 2}`}
                  />
                </g>
              )
            })}
            {room.armies.map((army, index) => {
              const place = placeOf(army, epoch)
              const spot = at(place.region)
              if (!spot) return null
              const offset = (index % 3) - 1
              return (
                <g key={`army.${army.army?.id ?? index}`}>
                  <title>{`${army.army?.name ?? 'An army'}: ${army.size} soldiers`}</title>
                  <circle
                    cx={spot.x + offset * unit * 10}
                    cy={spot.y + unit * 14}
                    r={
                      unit *
                      (5 + Math.min(5, Math.log10(Math.max(1, army.size))))
                    }
                    className={`${SIDE_FILL[side(army.owner?.id) % SIDE_FILL.length]} stroke-background`}
                    strokeWidth={unit * 2}
                  />
                </g>
              )
            })}
          </svg>
        </div>
        <div className='flex min-w-0 flex-col gap-3 @3xl/mil:col-span-2'>
          <EpochSlider
            value={epoch}
            min={epochs[0] ?? room.war.started_epoch}
            max={epochs.at(-1) ?? room.war.started_epoch}
            label='Epoch'
            onChange={setPicked}
          />
          <div className='grid min-w-0 grid-cols-2 gap-2'>
            <IconStat
              icon={Flag}
              label='Fronts'
              value={fronts.length}
              tone='danger'
            />
            <IconStat
              icon={Swords}
              label='Battles'
              value={battles.length}
              tone='warning'
            />
            <IconStat
              icon={Castle}
              label='Sieges'
              value={sieges.length}
              tone='gold'
            />
            <IconStat
              icon={Users}
              label='Armies'
              value={room.armies.length}
              tone='info'
            />
          </div>
          <Legend sides={sides} room={room} epoch={epoch} where={names} />
        </div>
      </div>
    </Panel>
  )
}

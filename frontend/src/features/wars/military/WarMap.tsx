import { useMemo, useState } from 'react'
import { Map as MapIcon } from 'lucide-react'
import { EmptyState, EpochSlider } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import type { ArmyCard, WarRoom } from './api'
import { nameOf } from './depth'
import { STANCE } from './labels'
import { Panel, Tag } from './parts'

const SIZE = 320
const RADIUS = 120
const CENTER = SIZE / 2
const SIDE_TONES = [
  'fill-destructive',
  'fill-info',
  'fill-warning',
  'fill-success',
]

type Spot = { id: number; name: string; x: number; y: number }

function placeOf(
  army: ArmyCard,
  epoch: number
): { region: number | null; stance: string } {
  const moves = army.movements.filter((move) => move.epoch <= epoch)
  const last = moves.at(-1)
  return last
    ? { region: last.to_region?.id ?? null, stance: last.stance }
    : { region: army.region?.id ?? null, stance: army.stance }
}

export function WarMap({ room }: { room: WarRoom }) {
  const epochs = useMemo(() => {
    const seen = new Set<number>([room.war.started_epoch])
    room.armies.forEach((army) =>
      army.movements.forEach((move) => seen.add(move.epoch))
    )
    room.fronts.forEach((front) => seen.add(front.last_epoch))
    return [...seen].sort((first, second) => first - second)
  }, [room])
  const [epoch, setEpoch] = useState(epochs.at(-1) ?? room.war.started_epoch)
  const regions = useMemo(() => {
    const found = new Map<number, string>()
    room.armies.forEach((army) => {
      if (army.region) found.set(army.region.id, army.region.name)
      army.movements.forEach((move) => {
        if (move.from_region)
          found.set(move.from_region.id, move.from_region.name)
        if (move.to_region) found.set(move.to_region.id, move.to_region.name)
      })
    })
    room.fronts.forEach((front) => {
      if (front.first_region)
        found.set(front.first_region.id, front.first_region.name)
      if (front.second_region)
        found.set(front.second_region.id, front.second_region.name)
    })
    room.occupations.forEach((occupation) => {
      if (occupation.region)
        found.set(occupation.region.id, occupation.region.name)
    })
    return [...found.entries()]
  }, [room])
  const spots: Spot[] = regions.map(([id, name], index) => {
    const angle =
      (index / Math.max(1, regions.length)) * Math.PI * 2 - Math.PI / 2
    return {
      id,
      name,
      x: CENTER + RADIUS * Math.cos(angle),
      y: CENTER + RADIUS * Math.sin(angle),
    }
  })
  const where = new Map(spots.map((spot) => [spot.id, spot]))
  const owners = [...new Set(room.armies.map((army) => army.owner?.id ?? 0))]
  const fronts = room.fronts.filter((front) => front.since_epoch <= epoch)
  if (spots.length === 0) {
    return (
      <Panel title='War map' icon={MapIcon} tone='verdigris'>
        <EmptyState
          icon={MapIcon}
          title='No marches yet'
          description='The armies have not moved; the map fills as they march.'
        />
      </Panel>
    )
  }
  return (
    <Panel
      title='War map'
      icon={MapIcon}
      tone='verdigris'
      hint='Fronts, marches and armies, scrubbed epoch by epoch'
    >
      <div
        data-surface='WarMap'
        className='flex min-w-0 flex-col gap-3 @2xl/mil:flex-row'
      >
        <svg
          viewBox={`0 0 ${SIZE} ${SIZE}`}
          role='img'
          aria-label='War map'
          className='aspect-square w-full max-w-sm shrink-0 rounded-lg border bg-background'
        >
          {fronts.map((front) => {
            const first = front.first_region
              ? where.get(front.first_region.id)
              : undefined
            const second = front.second_region
              ? where.get(front.second_region.id)
              : undefined
            if (!first || !second) return null
            return (
              <line
                key={`${front.first_region?.id}.${front.second_region?.id}`}
                x1={first.x}
                y1={first.y}
                x2={second.x}
                y2={second.y}
                className='stroke-destructive'
                strokeWidth={3}
                strokeDasharray='6 4'
              />
            )
          })}
          {room.armies.map((army) => {
            const trail = army.movements
              .filter(
                (move) =>
                  move.epoch <= epoch && move.from_region && move.to_region
              )
              .map(
                (move) =>
                  [
                    where.get(move.from_region!.id),
                    where.get(move.to_region!.id),
                  ] as const
              )
            return trail.map(([from, to], index) =>
              from && to ? (
                <line
                  key={`${army.army?.id}.${index}`}
                  x1={from.x}
                  y1={from.y}
                  x2={to.x}
                  y2={to.y}
                  className='stroke-muted-foreground'
                  strokeWidth={1.5}
                />
              ) : null
            )
          })}
          {spots.map((spot) => (
            <g key={spot.id}>
              <circle
                cx={spot.x}
                cy={spot.y}
                r={6}
                className='fill-muted stroke-border'
              />
              <text
                x={spot.x}
                y={spot.y - 10}
                textAnchor='middle'
                className='fill-foreground'
                fontSize={10}
              >
                {spot.name.length > 14
                  ? `${spot.name.slice(0, 13)}…`
                  : spot.name}
              </text>
            </g>
          ))}
          {room.armies.map((army, index) => {
            const place = placeOf(army, epoch)
            const spot =
              place.region !== null ? where.get(place.region) : undefined
            if (!spot) return null
            const tone =
              SIDE_TONES[
                owners.indexOf(army.owner?.id ?? 0) % SIDE_TONES.length
              ]
            return (
              <circle
                key={army.army?.id ?? index}
                cx={spot.x + 8 * (index % 3) - 8}
                cy={spot.y + 12}
                r={7}
                className={`${tone} stroke-background`}
                strokeWidth={2}
              />
            )
          })}
        </svg>
        <div className='flex min-w-0 flex-1 flex-col gap-2'>
          <EpochSlider
            value={epoch}
            min={epochs[0] ?? room.war.started_epoch}
            max={epochs.at(-1) ?? room.war.started_epoch}
            label='Epoch'
            onChange={setEpoch}
          />
          <ul className='flex min-w-0 flex-col gap-1.5'>
            {room.armies.map((army, index) => {
              const place = placeOf(army, epoch)
              const spot =
                place.region !== null ? where.get(place.region) : undefined
              return (
                <li
                  key={army.army?.id ?? index}
                  className='flex min-w-0 flex-wrap items-center gap-1.5'
                >
                  <Text as='span' truncate>
                    {army.army?.name ?? 'An army'}
                  </Text>
                  <Tag item={nameOf(STANCE, place.stance)} />
                  <Muted as='span' variant='caption'>
                    {spot ? spot.name : 'off the map'}
                  </Muted>
                </li>
              )
            })}
          </ul>
          <Muted variant='caption'>
            {fronts.length} fronts by epoch {epoch}
          </Muted>
        </div>
      </div>
    </Panel>
  )
}

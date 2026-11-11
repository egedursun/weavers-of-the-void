import { type ReactNode, Suspense, useMemo, useState } from 'react'
import { Html } from '@react-three/drei'
import { cn } from '@/lib/utils'
import { Text } from '@/components/typography'
import { tokenHex } from '@/features/cosmography/visual/palette'
import { DISTRICT_SPEC } from '@/features/entity/society/labels'
import { Model } from './Model'
import { SceneFrame } from './SceneFrame'
import { ZoneDot } from './ZoneDot'
import { type CityBuilding, type CityDistrict, type CityScene } from './api'
import {
  type Cell,
  cellKey,
  hexDistance,
  hexRing,
  hexToWorld,
  slotOffset,
  waterDirection,
} from './hex'
import { STATES, ZONES } from './labels'
import {
  DISTRICT_DRESS,
  GROUND_TILE,
  HOUSING_LOOK,
  type Part,
  SHELTER,
  STAGE_LOOK,
  STRUCTURE_LOOK,
  WALL,
  WALL_GATE,
  WALL_TOWER,
  WATER_TILE,
  stageOf,
} from './models'

export type CityPick =
  | { kind: 'district'; id: number }
  | { kind: 'building'; id: number }
  | { kind: 'cell'; q: number; r: number }
  | null

export type Zone = CityDistrict['zone']

const TOWER_EVERY = 4
const GATES = 4
const WATER_DEPTH = 4
const COUNTRYSIDE = 3
const HOUSE_SLOTS = 6
const SHARED_SCALE = 0.62
const DAMAGED_DIM = 0.55
const FADED = 0.3
const SELECTED_LIFT = 0.12

type Hover = { x: number; z: number; text: string } | null

function houseSlots(
  district: CityDistrict,
  used: Map<string, number>
): [Cell, number][] {
  const found: [Cell, number][] = []
  for (const raw of district.cells) {
    const cell: Cell = [raw[0], raw[1]]
    for (
      let slot = used.get(cellKey(cell)) ?? 0;
      slot <= HOUSE_SLOTS;
      slot += 1
    )
      found.push([cell, slot])
  }
  return found
}

function buildingParts(building: CityBuilding): Part[] {
  const stage = stageOf(building.state, building.progress)
  return stage ? [STAGE_LOOK[stage]] : [...STRUCTURE_LOOK[building.kind]]
}

function describeBuilding(building: CityBuilding): string {
  return `${building.node.name} · level ${building.level} · ${STATES[building.state].toLowerCase()}${building.state === 'building' ? ` ${building.progress}%` : ''} · condition ${building.condition}%`
}

function describeDistrict(district: CityDistrict): string {
  return `${DISTRICT_SPEC[district.kind].label} · level ${district.level} · ${district.dwellings} homes · desirability ${district.desirability}`
}

function footprint(scene: CityScene): { center: Cell; radius: number } {
  const cells = scene.districts.flatMap((district) =>
    district.cells.map((cell) => [cell[0], cell[1]] as Cell)
  )
  if (cells.length === 0) return { center: [0, 0], radius: 3 }
  const q = Math.round(
    cells.reduce((sum, cell) => sum + cell[0], 0) / cells.length
  )
  const r = Math.round(
    cells.reduce((sum, cell) => sum + cell[1], 0) / cells.length
  )
  const center: Cell = [q, r]
  const radius = Math.max(
    2,
    ...cells.map((cell) => hexDistance(cell, center)),
    scene.walls_radius ? scene.walls_radius + hexDistance(center, [0, 0]) : 0
  )
  return { center, radius }
}

function around(center: Cell, radius: number): Cell[] {
  return Array.from({ length: radius + 1 }, (_, step) =>
    hexRing(step).map(
      (cell) => [cell[0] + center[0], cell[1] + center[1]] as Cell
    )
  ).flat()
}

export default function CityScene3D({
  scene,
  selected,
  moving,
  onPick,
  fallback,
  shown = null,
  labels = true,
}: {
  scene: CityScene
  selected: CityPick
  moving: number | null
  onPick: (pick: CityPick) => void
  fallback: ReactNode
  shown?: ReadonlySet<Zone> | null
  labels?: boolean
}) {
  const [hover, setHover] = useState<Hover>(null)
  const occupied = useMemo(() => {
    const found = new Map<string, number>()
    for (const building of scene.buildings) {
      const key = cellKey([building.q, building.r])
      found.set(key, (found.get(key) ?? 0) + 1)
    }
    return found
  }, [scene.buildings])
  const { center, radius } = footprint(scene)
  const visible = (zone: Zone) => shown === null || shown.has(zone)
  const cells = scene.districts.flatMap((district) =>
    district.cells.map((cell) => ({
      district,
      cell: [cell[0], cell[1]] as Cell,
    }))
  )
  const built = new Set(cells.map(({ cell }) => cellKey(cell)))
  const ringCells = scene.walls_radius ? hexRing(scene.walls_radius) : []
  const wallKeys = new Set(ringCells.map(cellKey))
  const water: Cell[] = []
  if (scene.water_side !== null) {
    const [dq, dr] = waterDirection(scene.water_side)
    for (const cell of around(center, radius + WATER_DEPTH))
      if (
        !built.has(cellKey(cell)) &&
        (cell[0] - center[0]) * dq + (cell[1] - center[1]) * dr > radius * 0.55
      )
        water.push(cell)
  }
  const wet = new Set(water.map(cellKey))
  const countryside = around(center, radius + COUNTRYSIDE).filter(
    (cell) =>
      !built.has(cellKey(cell)) &&
      !wet.has(cellKey(cell)) &&
      !wallKeys.has(cellKey(cell))
  )
  const homes = scene.districts
    .filter((district) => visible(district.zone))
    .flatMap((district) => {
      const shownHomes = Math.ceil(district.dwellings / scene.scale)
      return houseSlots(district, occupied)
        .slice(0, shownHomes)
        .map(([cell, slot]) => ({ district, cell, slot }))
    })
  const slumCells = scene.districts
    .filter((district) => district.kind === 'slums')
    .flatMap((district) => district.cells)
  const shelterCells: Cell[] = (
    slumCells.length ? slumCells : hexRing((scene.walls_radius ?? radius) + 1)
  ).map((cell) => [cell[0], cell[1]])
  const shelters = Array.from(
    { length: Math.ceil(scene.shelters / scene.scale) },
    (_, index) => ({
      cell: shelterCells[index % Math.max(1, shelterCells.length)],
      slot:
        Math.floor(index / Math.max(1, shelterCells.length)) %
        (HOUSE_SLOTS + 1),
    })
  )
  const zoneOf = new Map(scene.districts.map((row) => [row.id, row.zone]))
  const pickDistrict = (id: number) => onPick({ kind: 'district', id })
  const [focusX, focusZ] = hexToWorld(center[0], center[1])
  const countrysideTint = tokenHex('--success')
  return (
    <SceneFrame
      label={`City of ${scene.town.name}`}
      reach={(radius + 1) * 2}
      center={[focusX, focusZ]}
      fallback={fallback}
    >
      <Suspense fallback={null}>
        {countryside.map((cell) => {
          const [x, z] = hexToWorld(cell[0], cell[1])
          return (
            <Model
              key={`land-${cellKey(cell)}`}
              part={{ model: GROUND_TILE }}
              x={x}
              z={z}
              y={-0.06}
              tint={countrysideTint}
              dim={0.8}
              onClick={
                moving !== null
                  ? () => onPick({ kind: 'cell', q: cell[0], r: cell[1] })
                  : undefined
              }
            />
          )
        })}
        {cells.map(({ district, cell }) => {
          const [x, z] = hexToWorld(cell[0], cell[1])
          const chosen =
            selected?.kind === 'district' && selected.id === district.id
          return (
            <Model
              key={`ground-${cellKey(cell)}`}
              part={{ model: GROUND_TILE }}
              x={x}
              z={z}
              y={chosen ? SELECTED_LIFT : 0}
              tint={tokenHex(ZONES[district.zone].token)}
              dim={
                !visible(district.zone)
                  ? FADED
                  : district.condition < 50
                    ? DAMAGED_DIM + district.condition / 200
                    : 1
              }
              onClick={() =>
                moving !== null
                  ? onPick({ kind: 'cell', q: cell[0], r: cell[1] })
                  : pickDistrict(district.id)
              }
              onPointerOver={() =>
                setHover({ x, z, text: describeDistrict(district) })
              }
              onPointerOut={() => setHover(null)}
            />
          )
        })}
        {water.map((cell) => {
          const [x, z] = hexToWorld(cell[0], cell[1])
          return (
            <Model
              key={`water-${cellKey(cell)}`}
              part={{ model: WATER_TILE }}
              x={x}
              z={z}
            />
          )
        })}
        {scene.districts
          .filter((district) => visible(district.zone))
          .flatMap((district) =>
            (DISTRICT_DRESS[district.kind] ?? []).flatMap((part) =>
              district.cells
                .filter((cell) => !occupied.has(cellKey([cell[0], cell[1]])))
                .map((cell) => {
                  const [x, z] = hexToWorld(cell[0], cell[1])
                  return (
                    <Model
                      key={`dress-${district.id}-${cellKey([cell[0], cell[1]])}-${part.model}`}
                      part={part}
                      x={x}
                      z={z}
                      onClick={() => pickDistrict(district.id)}
                    />
                  )
                })
            )
          )}
        {scene.buildings
          .filter((building) =>
            visible(
              (building.district_id !== null
                ? zoneOf.get(building.district_id)
                : undefined) ?? building.zone
            )
          )
          .flatMap((building) => {
            const [cx, cz] = hexToWorld(building.q, building.r)
            const [ox, oz] = slotOffset(building.slot)
            const shared =
              (occupied.get(cellKey([building.q, building.r])) ?? 1) > 1
            const chosen =
              selected?.kind === 'building' && selected.id === building.node.id
            return buildingParts(building).map((part, index) => (
              <Model
                key={`building-${building.node.id}-${index}`}
                part={part}
                x={cx + (shared ? ox : 0)}
                z={cz + (shared ? oz : 0)}
                y={chosen ? SELECTED_LIFT * 3 : 0}
                scale={shared ? SHARED_SCALE : 1}
                tint={chosen ? tokenHex('--brand-gold') : null}
                dim={
                  building.state === 'damaged'
                    ? DAMAGED_DIM
                    : building.state === 'ruined'
                      ? FADED
                      : 1
                }
                onClick={() =>
                  onPick({ kind: 'building', id: building.node.id })
                }
                onPointerOver={() =>
                  setHover({
                    x: cx + ox,
                    z: cz + oz,
                    text: describeBuilding(building),
                  })
                }
                onPointerOut={() => setHover(null)}
              />
            ))
          })}
        {homes.map(({ district, cell, slot }) => {
          const [cx, cz] = hexToWorld(cell[0], cell[1])
          const [ox, oz] = slotOffset(slot)
          return (
            <Model
              key={`home-${district.id}-${cellKey(cell)}-${slot}`}
              part={HOUSING_LOOK[district.housing]}
              x={cx + ox}
              z={cz + oz}
              onClick={() => pickDistrict(district.id)}
            />
          )
        })}
        {shelters.map(({ cell, slot }, index) => {
          const [cx, cz] = hexToWorld(cell[0], cell[1])
          const [ox, oz] = slotOffset(slot)
          return (
            <Model
              key={`shelter-${index}`}
              part={SHELTER}
              x={cx + ox}
              z={cz + oz}
            />
          )
        })}
        {ringCells.map((cell, index) => {
          const [x, z] = hexToWorld(cell[0], cell[1])
          const gate =
            index % Math.max(1, Math.floor(ringCells.length / GATES)) === 0
          const tower = index % TOWER_EVERY === TOWER_EVERY - 1
          return (
            <Model
              key={`wall-${cellKey(cell)}`}
              part={{
                model: tower ? WALL_TOWER : gate ? WALL_GATE : WALL,
                scale: tower ? 0.6 : 0.9,
                turn: Math.atan2(x, z) + Math.PI / 2,
              }}
              x={x}
              z={z}
            />
          )
        })}
        {labels &&
          scene.districts
            .filter((district) => visible(district.zone))
            .map((district) => {
              const [x, z] = hexToWorld(district.q, district.r)
              const chosen =
                selected?.kind === 'district' && selected.id === district.id
              return (
                <Html
                  key={`label-${district.id}`}
                  position={[x, 1.4, z]}
                  center
                  zIndexRange={[10, 0]}
                >
                  <div
                    className={cn(
                      'pointer-events-none flex items-center gap-1.5 rounded-full border bg-popover/90 px-2 py-0.5 whitespace-nowrap text-popover-foreground shadow-sm backdrop-blur-sm',
                      chosen && 'border-primary'
                    )}
                  >
                    <ZoneDot spec={ZONES[district.zone]} />
                    <Text as='span' variant='caption' tone='inherit'>
                      {`${DISTRICT_SPEC[district.kind].label} ${district.level}`}
                    </Text>
                  </div>
                </Html>
              )
            })}
        {hover && (
          <Html position={[hover.x, 2, hover.z]} center zIndexRange={[20, 0]}>
            <div className='pointer-events-none rounded-md border bg-popover px-2 py-1 whitespace-nowrap text-popover-foreground shadow-md'>
              <Text as='span' variant='caption' tone='inherit'>
                {hover.text}
              </Text>
            </div>
          </Html>
        )}
      </Suspense>
    </SceneFrame>
  )
}

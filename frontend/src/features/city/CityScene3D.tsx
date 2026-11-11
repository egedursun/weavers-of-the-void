import { type ReactNode, Suspense, useMemo, useState } from 'react'
import { Html } from '@react-three/drei'
import { tokenHex } from '@/features/cosmography/visual/palette'
import { Model } from './Model'
import { SceneFrame } from './SceneFrame'
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
import { ZONES } from './labels'
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

const TOWER_EVERY = 4
const GATES = 4
const WATER_DEPTH = 3
const HOUSE_SLOTS = 6
const SHARED_SCALE = 0.55
const DAMAGED_DIM = 0.55
const SELECTED_LIFT = 0.08

type Hover = { x: number; z: number; text: string } | null

function houseSlots(
  district: CityDistrict,
  used: Map<string, number>
): [Cell, number][] {
  const found: [Cell, number][] = []
  for (const raw of district.cells) {
    const cell: Cell = [raw[0], raw[1]]
    const taken = used.get(cellKey(cell)) ?? 0
    for (let slot = taken === 0 ? 0 : taken; slot <= HOUSE_SLOTS; slot += 1)
      found.push([cell, slot])
  }
  return found
}

function buildingParts(building: CityBuilding): Part[] {
  const stage = stageOf(building.state, building.progress)
  return stage ? [STAGE_LOOK[stage]] : [...STRUCTURE_LOOK[building.kind]]
}

function describeBuilding(building: CityBuilding): string {
  return `${building.node.name} · level ${building.level} · condition ${building.condition}% · ${building.state}${building.state === 'building' ? ` ${building.progress}%` : ''}`
}

function describeDistrict(district: CityDistrict): string {
  return `${district.kind.replaceAll('_', ' ')} · level ${district.level} · ${district.dwellings} homes (${district.housing}) · desirability ${district.desirability}`
}

export default function CityScene3D({
  scene,
  selected,
  moving,
  onPick,
  fallback,
}: {
  scene: CityScene
  selected: CityPick
  moving: number | null
  onPick: (pick: CityPick) => void
  fallback: ReactNode
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
  const cells = scene.districts.flatMap((district) =>
    district.cells.map((cell) => ({
      district,
      cell: [cell[0], cell[1]] as Cell,
    }))
  )
  const reach = Math.max(
    3,
    ...cells.map(({ cell }) => hexDistance(cell, [0, 0]) + 1),
    (scene.walls_radius ?? 0) + 1
  )
  const free = new Set(cells.map(({ cell }) => cellKey(cell)))
  const ringCells = scene.walls_radius ? hexRing(scene.walls_radius) : []
  const water: Cell[] = []
  if (scene.water_side !== null) {
    const [dq, dr] = waterDirection(scene.water_side)
    for (let depth = 1; depth <= WATER_DEPTH; depth += 1)
      for (const cell of hexRing(reach + depth))
        if (cell[0] * dq + cell[1] * dr > reach * 0.6) water.push(cell)
  }
  const homes = scene.districts.flatMap((district) => {
    const shown = Math.ceil(district.dwellings / scene.scale)
    return houseSlots(district, occupied)
      .slice(0, shown)
      .map(([cell, slot]) => ({ district, cell, slot }))
  })
  const slumCells = scene.districts
    .filter((district) => district.kind === 'slums')
    .flatMap((district) => district.cells)
  const shelterCells: Cell[] = (
    slumCells.length
      ? slumCells
      : ringCells.length
        ? hexRing((scene.walls_radius ?? reach) + 1)
        : hexRing(reach)
  ).map((cell) => [cell[0], cell[1]])
  const shelters = Array.from(
    { length: Math.ceil(scene.shelters / scene.scale) },
    (_, index) => ({
      cell:
        shelterCells[index % Math.max(1, shelterCells.length)] ??
        ([0, 0] as Cell),
      slot:
        Math.floor(index / Math.max(1, shelterCells.length)) %
        (HOUSE_SLOTS + 1),
    })
  )
  const pickDistrict = (id: number) => onPick({ kind: 'district', id })
  return (
    <SceneFrame
      label={`City of ${scene.town.name}`}
      reach={reach}
      fallback={fallback}
    >
      <Suspense fallback={null}>
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
                district.condition < 50
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
        {moving !== null &&
          hexRing(0)
            .concat(
              ...Array.from({ length: reach + 1 }, (_, radius) =>
                hexRing(radius + 1)
              )
            )
            .filter((cell) => !free.has(cellKey(cell)))
            .map((cell) => {
              const [x, z] = hexToWorld(cell[0], cell[1])
              return (
                <Model
                  key={`spare-${cellKey(cell)}`}
                  part={{ model: GROUND_TILE }}
                  x={x}
                  z={z}
                  y={-0.1}
                  dim={0.6}
                  onClick={() =>
                    onPick({ kind: 'cell', q: cell[0], r: cell[1] })
                  }
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
        {scene.districts.flatMap((district) =>
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
        {scene.buildings.flatMap((building) => {
          const [cx, cz] = hexToWorld(building.q, building.r)
          const [ox, oz] = slotOffset(building.slot)
          const shared =
            (occupied.get(cellKey([building.q, building.r])) ?? 1) > 1
          const scale = shared ? SHARED_SCALE : 1
          const chosen =
            selected?.kind === 'building' && selected.id === building.node.id
          return buildingParts(building).map((part, index) => (
            <Model
              key={`building-${building.node.id}-${index}`}
              part={part}
              x={cx + ox}
              z={cz + oz}
              y={chosen ? SELECTED_LIFT * 3 : 0}
              scale={scale}
              tint={chosen ? tokenHex('--brand-gold') : null}
              dim={building.state === 'damaged' ? DAMAGED_DIM : 1}
              onClick={() => onPick({ kind: 'building', id: building.node.id })}
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
        {hover && (
          <Html position={[hover.x, 1.6, hover.z]} center zIndexRange={[20, 0]}>
            <div className='pointer-events-none rounded-md border bg-popover px-2 py-1 whitespace-nowrap text-popover-foreground shadow-sm'>
              {hover.text}
            </div>
          </Html>
        )}
      </Suspense>
    </SceneFrame>
  )
}

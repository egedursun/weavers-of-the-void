import { type ReactNode, Suspense, useMemo, useState } from 'react'
import { Html } from '@react-three/drei'
import { plural } from '@/lib/units'
import { Text } from '@/components/typography'
import { tokenHex } from '@/features/cosmography/visual/palette'
import { DISTRICT_SPEC } from '@/features/entity/society/labels'
import { InstancedModel } from './InstancedModel'
import { Model } from './Model'
import { SceneFrame } from './SceneFrame'
import { type SceneLabel, SceneLabels } from './SceneLabels'
import { type CityBuilding, type CityDistrict, type CityScene } from './api'
import { roadDress, roadPaths, roadTiles, wallPieces } from './cityWalls'
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
  typedLook,
  ROAD_DRESS,
  ROAD_LOOK,
  WALL_LOOK,
  WATER_TILE,
  stageOf,
} from './models'

export type CityPick =
  | { kind: 'district'; id: number }
  | { kind: 'building'; id: number }
  | { kind: 'cell'; q: number; r: number }
  | null

export type Zone = CityDistrict['zone']

const WATER_DEPTH = 4
const COUNTRYSIDE = 3
const HOUSE_SLOTS = 6
const SHARED_SCALE = 0.62
const DAMAGED_DIM = 0.55
const FADED = 0.3
const SELECTED_LIFT = 0.12
const FIELDS: ReadonlySet<CityDistrict['kind']> = new Set([
  'farmland',
  'necropolis',
])

type Hover = { x: number; z: number; text: string } | null

function freeSlots(
  cells: readonly Cell[],
  used: Map<string, number>
): [Cell, number][] {
  return cells
    .filter((cell) => !used.has(cellKey(cell)))
    .flatMap((cell) =>
      Array.from(
        { length: HOUSE_SLOTS },
        (_, index) => [cell, index + 1] as [Cell, number]
      )
    )
}

function cellsOf(district: CityDistrict): Cell[] {
  return district.cells.map((raw) => [raw[0], raw[1]] as Cell)
}

function buildingParts(building: CityBuilding): Part[] {
  const stage = stageOf(building.state, building.progress)
  return stage
    ? [STAGE_LOOK[stage]]
    : typedLook(building.kind, building.form, building.storeys)
}

function describeBuilding(building: CityBuilding): string {
  return `${building.node.name} · level ${building.level} · ${STATES[building.state].toLowerCase()}${building.state === 'building' ? ` ${building.progress}%` : ''} · condition ${building.condition}%`
}

function describeDistrict(district: CityDistrict): string {
  return `${DISTRICT_SPEC[district.kind].label} · level ${district.level} · ${plural(district.dwellings, 'home', 'homes')} · desirability ${district.desirability}`
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

function placeAt(
  cell: Cell,
  part?: Part
): { x: number; z: number; scale: number; turn: number } {
  const [x, z] = hexToWorld(cell[0], cell[1])
  const [dx, dz] = part?.offset ?? [0, 0]
  const scale = part?.scale ?? 1
  return { x: x + dx, z: z + dz, scale, turn: part?.turn ?? 0 }
}

function grouped<T extends { part: Part }>(items: T[]): [string, T[]][] {
  const found = new Map<string, T[]>()
  for (const item of items)
    found.set(item.part.model, [...(found.get(item.part.model) ?? []), item])
  return [...found.entries()]
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
  const shore = Math.max(
    scene.walls_radius ?? 0,
    ...cells
      .filter(({ district }) => !FIELDS.has(district.kind))
      .map(({ cell }) => hexDistance(cell, [0, 0]))
  )
  const water: Cell[] = []
  if (scene.water_side !== null) {
    const [dq, dr] = waterDirection(scene.water_side)
    for (const cell of around(center, radius + WATER_DEPTH))
      if (
        !built.has(cellKey(cell)) &&
        hexDistance(cell, [0, 0]) > shore &&
        cell[0] * dq + cell[1] * dr > 0
      )
        water.push(cell)
  }
  const wet = new Set(water.map(cellKey))
  const roadReach =
    COUNTRYSIDE + Math.max(0, radius - (scene.walls_radius ?? radius))
  const offRoad = (cell: Cell) =>
    built.has(cellKey(cell)) || wet.has(cellKey(cell))
  const roadRadius = scene.walls_radius ?? radius
  const paths = roadPaths(roadRadius, scene.roads, roadReach, offRoad).map(
    (path) => {
      const dry = path.findIndex(
        (cell, index) => index > 0 && wet.has(cellKey(cell))
      )
      return dry === -1 ? path : path.slice(0, dry)
    }
  )
  const roads = roadTiles(roadRadius, scene.roads, roadReach, offRoad).filter(
    (tile) => !offRoad(tile.cell)
  )
  const dress = roadDress(paths, scene.roads, roadRadius)
  const roadCells = new Set(roads.map((tile) => cellKey(tile.cell)))
  const countryside = around(center, radius + COUNTRYSIDE).filter(
    (cell) =>
      !built.has(cellKey(cell)) &&
      !wet.has(cellKey(cell)) &&
      !roadCells.has(cellKey(cell))
  )
  const walls = wallPieces(
    scene.walls_radius ?? 0,
    scene.walls_level,
    scene.roads
  ).filter((piece) => !occupied.has(cellKey(piece.cell)))
  const names: SceneLabel[] = scene.districts
    .filter((district) => visible(district.zone) && district.cells.length > 0)
    .map((district) => {
      const points = district.cells.map((cell) => hexToWorld(cell[0], cell[1]))
      return {
        id: String(district.id),
        x: points.reduce((sum, point) => sum + point[0], 0) / points.length,
        z: points.reduce((sum, point) => sum + point[1], 0) / points.length,
        text: `${DISTRICT_SPEC[district.kind].label} ${district.level}`,
        fill: ZONES[district.zone].fill,
        rank: district.level * 10 + district.cells.length,
        chosen: selected?.kind === 'district' && selected.id === district.id,
      }
    })
  const homeSlots = new Map(
    scene.districts.map((district) => [
      district.id,
      freeSlots(cellsOf(district), occupied),
    ])
  )
  const homes = scene.districts
    .filter((district) => visible(district.zone))
    .flatMap((district) =>
      (homeSlots.get(district.id) ?? [])
        .slice(0, Math.ceil(district.dwellings / scene.scale))
        .map(([cell, slot]) => ({ district, cell, slot }))
    )
  const slumSlots = scene.districts
    .filter((district) => district.kind === 'slums')
    .flatMap((district) =>
      (homeSlots.get(district.id) ?? []).slice(
        Math.ceil(district.dwellings / scene.scale)
      )
    )
  const camp = freeSlots(
    hexRing((scene.walls_radius ?? radius) + 1).filter(
      (cell) => !built.has(cellKey(cell)) && !wet.has(cellKey(cell))
    ),
    occupied
  )
  const shelters = [...slumSlots, ...camp]
    .slice(0, Math.ceil(scene.shelters / scene.scale))
    .map(([cell, slot]) => ({ cell, slot }))
  const zoneOf = new Map(scene.districts.map((row) => [row.id, row.zone]))
  const pickDistrict = (id: number) => onPick({ kind: 'district', id })
  const [focusX, focusZ] = hexToWorld(center[0], center[1])
  return (
    <SceneFrame
      label={`City of ${scene.town.name}`}
      reach={(radius + 1) * 2}
      center={[focusX, focusZ]}
      fallback={fallback}
    >
      <Suspense fallback={null}>
        <InstancedModel
          model={GROUND_TILE}
          items={countryside.map((cell) => ({
            cell,
            ...placeAt(cell),
            y: -0.06,
          }))}
          onPick={
            moving !== null
              ? (item) =>
                  onPick({ kind: 'cell', q: item.cell[0], r: item.cell[1] })
              : undefined
          }
        />
        {scene.districts.map((district) => {
          const chosen =
            selected?.kind === 'district' && selected.id === district.id
          return (
            <InstancedModel
              key={`ground-${district.id}`}
              model={GROUND_TILE}
              items={district.cells.map((raw) => {
                const cell: Cell = [raw[0], raw[1]]
                return {
                  cell,
                  ...placeAt(cell),
                  y: chosen ? SELECTED_LIFT : 0,
                }
              })}
              tint={tokenHex(ZONES[district.zone].token)}
              dim={
                !visible(district.zone)
                  ? FADED
                  : district.condition < 50
                    ? DAMAGED_DIM + district.condition / 200
                    : 1
              }
              onPick={(item) =>
                moving !== null
                  ? onPick({ kind: 'cell', q: item.cell[0], r: item.cell[1] })
                  : pickDistrict(district.id)
              }
              onHover={(item) =>
                setHover(
                  item
                    ? { x: item.x, z: item.z, text: describeDistrict(district) }
                    : null
                )
              }
            />
          )
        })}
        <InstancedModel
          model={WATER_TILE}
          items={water.map((cell) => placeAt(cell))}
        />
        {grouped(
          scene.districts
            .filter((district) => visible(district.zone))
            .flatMap((district) =>
              (DISTRICT_DRESS[district.kind] ?? []).flatMap((part) =>
                district.cells
                  .filter((cell) => !occupied.has(cellKey([cell[0], cell[1]])))
                  .map((cell) => ({
                    part,
                    district: district.id,
                    ...placeAt([cell[0], cell[1]], part),
                  }))
              )
            )
        ).map(([model, items]) => (
          <InstancedModel
            key={`dress-${model}`}
            model={model}
            items={items}
            onPick={(item) => pickDistrict(item.district)}
          />
        ))}
        {scene.buildings
          .filter((building) =>
            visible(
              (building.home_district_id !== null
                ? zoneOf.get(building.home_district_id)
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
        {grouped(
          homes.map(({ district, cell, slot }) => {
            const part = HOUSING_LOOK[district.housing]
            const [ox, oz] = slotOffset(slot)
            const [x, z] = hexToWorld(cell[0], cell[1])
            return {
              part,
              district: district.id,
              x: x + ox,
              z: z + oz,
              scale: part.scale ?? 1,
            }
          })
        ).map(([model, items]) => (
          <InstancedModel
            key={`homes-${model}`}
            model={model}
            items={items}
            onPick={(item) => pickDistrict(item.district)}
          />
        ))}
        <InstancedModel
          model={SHELTER.model}
          items={shelters.map(({ cell, slot }) => {
            const [x, z] = hexToWorld(cell[0], cell[1])
            const [ox, oz] = slotOffset(slot)
            return { x: x + ox, z: z + oz, scale: SHELTER.scale ?? 1 }
          })}
        />
        {walls.map((piece) => {
          const [x, z] = hexToWorld(piece.cell[0], piece.cell[1])
          return (
            <Model
              key={piece.key}
              part={{
                ...WALL_LOOK[piece.model](scene.walls_level),
                turn: piece.turn,
              }}
              x={x}
              z={z}
            />
          )
        })}
        {grouped(
          roads.map((tile) => {
            const [x, z] = hexToWorld(tile.cell[0], tile.cell[1])
            return {
              part: { model: ROAD_LOOK[tile.model] },
              x,
              z,
              y: -0.06,
              turn: tile.turn,
            }
          })
        ).map(([model, items]) => (
          <InstancedModel key={`road-${model}`} model={model} items={items} />
        ))}
        {(['stone', 'lantern', 'cart'] as const).flatMap((kind) =>
          ROAD_DRESS[kind].map((part, index) => (
            <InstancedModel
              key={`dress-${kind}-${index}`}
              model={part.model}
              items={dress
                .filter((item) => item.kind === kind)
                .filter(
                  (_, at) =>
                    kind !== 'stone' || at % ROAD_DRESS.stone.length === index
                )
                .map((item) => {
                  const [dx, dz] = part.offset ?? [0, 0]
                  const cos = Math.cos(item.turn)
                  const sin = Math.sin(item.turn)
                  return {
                    x: item.x + dx * cos + dz * sin,
                    z: item.z - dx * sin + dz * cos,
                    y: 0.005,
                    scale: part.scale ?? 1,
                    turn: item.turn + (part.turn ?? 0),
                  }
                })}
            />
          ))
        )}
        {labels && <SceneLabels labels={names} />}
        {hover && (
          <Html position={[hover.x, 2, hover.z]} center zIndexRange={[20, 0]}>
            <div className='pointer-events-none rounded-md border surface-sheen border-gild/60 bg-card px-2 py-1 whitespace-nowrap text-popover-foreground'>
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

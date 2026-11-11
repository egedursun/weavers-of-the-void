import { type ReactNode, Suspense, useState } from 'react'
import { Html } from '@react-three/drei'
import { tokenHex } from '@/features/cosmography/visual/palette'
import { Model } from './Model'
import { SceneFrame } from './SceneFrame'
import { SceneLabels } from './SceneLabels'
import { type LandScene } from './api'
import { cellKey, hexDistance, hexRing, hexToWorld } from './hex'
import { COVERS, GROUNDS, STATES } from './labels'
import {
  RIVER_TILE,
  SETTLEMENT_LOOK,
  STAGE_LOOK,
  STRUCTURE_LOOK,
  coverLook,
  groundLook,
  placeLook,
  resourceLook,
  stageOf,
} from './models'

export type LandPick =
  | { kind: 'tile'; q: number; r: number }
  | { kind: 'settlement' | 'place' | 'work' | 'resource'; id: number }
  | null

const RIVER_SCALE = { none: 0, stream: 0.7, river: 1, great_river: 1.15 }
const RESOURCE_MIN = 0.45
const SPENT_DIM = 0.5
const SELECTED_LIFT = 0.25
const COAST_TURN = Math.PI / 3

type Hover = { x: number; z: number; text: string } | null

function townSize(population: number): { parts: number; scale: number } {
  const order = Math.log10(Math.max(1, population))
  return {
    parts: Math.max(1, Math.min(SETTLEMENT_LOOK.length, Math.ceil(order - 1))),
    scale: Math.min(1.4, 0.6 + order / 8),
  }
}

function remaining(reserve: number, initial: number): number {
  return initial > 0 ? Math.max(0, Math.min(1, reserve / initial)) : 1
}

export default function LandScene3D({
  scene,
  selected,
  onPick,
  fallback,
}: {
  scene: LandScene
  selected: LandPick
  onPick: (pick: LandPick) => void
  fallback: ReactNode
}) {
  const [hover, setHover] = useState<Hover>(null)
  const reach = Math.max(
    4,
    ...scene.tiles.map((tile) =>
      Math.max(Math.abs(tile.q), Math.abs(tile.r), Math.abs(tile.q + tile.r))
    )
  )
  const busy = new Set(
    [
      ...scene.settlements,
      ...scene.places,
      ...scene.works,
      ...scene.resources,
    ].map((item) => cellKey([item.q, item.r]))
  )
  const wetCells = new Set(
    scene.tiles
      .filter((tile) => tile.ground === 'water')
      .map((tile) => cellKey([tile.q, tile.r]))
  )
  const shorelineOf = (tile: LandScene['tiles'][number]): number | null => {
    const water = hexRing(1).find((step) =>
      wetCells.has(cellKey([tile.q + step[0], tile.r + step[1]]))
    )
    if (water) {
      const [x, z] = hexToWorld(water[0], water[1])
      return COAST_TURN - Math.atan2(z, x)
    }
    if (scene.coast === 'none' || hexDistance([tile.q, tile.r], [0, 0]) < reach)
      return null
    const [x, z] = hexToWorld(tile.q, tile.r)
    return COAST_TURN - Math.atan2(z, x)
  }
  const lifted = (kind: NonNullable<LandPick>['kind'], id: number) =>
    selected !== null &&
    selected.kind === kind &&
    'id' in selected &&
    selected.id === id
      ? SELECTED_LIFT
      : 0
  return (
    <SceneFrame
      label={`Land of ${scene.region.name}`}
      reach={reach * 2}
      fallback={fallback}
    >
      <Suspense fallback={null}>
        {scene.tiles.flatMap((tile) => {
          const [x, z] = hexToWorld(tile.q, tile.r)
          const chosen =
            selected?.kind === 'tile' &&
            selected.q === tile.q &&
            selected.r === tile.r
          const ground = tile.river
            ? [
                {
                  model: RIVER_TILE,
                  scale: RIVER_SCALE[scene.river],
                  turn: 0,
                },
              ]
            : groundLook(tile.ground, tile.q, tile.r, shorelineOf(tile))
          const cover = busy.has(cellKey([tile.q, tile.r]))
            ? []
            : coverLook(tile.cover, tile.q, tile.r)
          const pick = () => onPick({ kind: 'tile', q: tile.q, r: tile.r })
          const text = `${GROUNDS[tile.ground]} · ${COVERS[tile.cover]}${tile.river ? ' · river' : ''}`
          return [...ground, ...cover].map((part, index) => (
            <Model
              key={`tile-${cellKey([tile.q, tile.r])}-${index}`}
              part={part}
              x={x}
              z={z}
              y={chosen ? 0.1 : 0}
              tint={
                chosen && index === 0
                  ? tokenHex('--brand-gold')
                  : part.token
                    ? tokenHex(part.token)
                    : null
              }
              onClick={pick}
              onPointerOver={() => setHover({ x, z, text })}
              onPointerOut={() => setHover(null)}
            />
          ))
        })}
        {scene.settlements.flatMap((town) => {
          const [x, z] = hexToWorld(town.q, town.r)
          const size = townSize(Number(town.detail))
          return SETTLEMENT_LOOK.slice(0, size.parts).map((part, index) => (
            <Model
              key={`town-${town.node.id}-${index}`}
              part={part}
              x={x}
              z={z}
              y={lifted('settlement', town.node.id)}
              scale={size.scale}
              onClick={() => onPick({ kind: 'settlement', id: town.node.id })}
              onPointerOver={() =>
                setHover({
                  x,
                  z,
                  text: `${town.node.name} · ${town.detail} people`,
                })
              }
              onPointerOut={() => setHover(null)}
            />
          ))
        })}
        {scene.places.map((place) => {
          const [x, z] = hexToWorld(place.q, place.r)
          return (
            <Model
              key={`place-${place.node.id}`}
              part={placeLook(place.kind, place.sacred)}
              x={x}
              z={z}
              y={lifted('place', place.node.id)}
              onClick={() => onPick({ kind: 'place', id: place.node.id })}
              onPointerOver={() =>
                setHover({
                  x,
                  z,
                  text: `${place.node.name} · ${place.detail}`,
                })
              }
              onPointerOut={() => setHover(null)}
            />
          )
        })}
        {scene.works.flatMap((work) => {
          const [x, z] = hexToWorld(work.q, work.r)
          const stage = stageOf(work.state, work.progress)
          const parts = stage ? [STAGE_LOOK[stage]] : STRUCTURE_LOOK[work.kind]
          return parts.map((part, index) => (
            <Model
              key={`work-${work.node.id}-${index}`}
              part={part}
              x={x}
              z={z}
              y={lifted('work', work.node.id)}
              dim={work.condition < 50 ? SPENT_DIM + work.condition / 200 : 1}
              onClick={() => onPick({ kind: 'work', id: work.node.id })}
              onPointerOver={() =>
                setHover({
                  x,
                  z,
                  text: `${work.node.name} · level ${work.level} · ${STATES[work.state]}`,
                })
              }
              onPointerOut={() => setHover(null)}
            />
          ))
        })}
        {scene.resources.map((resource) => {
          const [x, z] = hexToWorld(resource.q, resource.r)
          const left = remaining(resource.reserve, resource.initial_reserve)
          const look = resourceLook(resource.commodity)
          return (
            <Model
              key={`resource-${resource.node.id}`}
              part={{
                ...look,
                scale:
                  (look.scale ?? 1) *
                  (RESOURCE_MIN +
                    (1 - RESOURCE_MIN) * (resource.richness / 100)),
              }}
              x={x}
              z={z}
              y={lifted('resource', resource.node.id)}
              dim={left < 0.25 ? SPENT_DIM : 1}
              onClick={() => onPick({ kind: 'resource', id: resource.node.id })}
              onPointerOver={() =>
                setHover({
                  x,
                  z,
                  text: `${resource.node.name} · richness ${resource.richness} · ${resource.reserve} of ${resource.initial_reserve} left`,
                })
              }
              onPointerOut={() => setHover(null)}
            />
          )
        })}
        <SceneLabels
          labels={[
            ...scene.places
              .filter(
                (place) =>
                  selected?.kind === 'place' && selected.id === place.node.id
              )
              .map((place) => {
                const [x, z] = hexToWorld(place.q, place.r)
                return {
                  id: `place-${place.node.id}`,
                  x,
                  z,
                  text: place.node.name,
                  fill: 'fill-zone-civic',
                  rank: -1,
                  chosen:
                    selected?.kind === 'place' && selected.id === place.node.id,
                }
              }),
            ...scene.settlements.map((town) => {
              const [x, z] = hexToWorld(town.q, town.r)
              return {
                id: String(town.node.id),
                x,
                z,
                text: town.node.name,
                fill: 'fill-zone-governance',
                rank: Number(town.detail) || 0,
                chosen:
                  selected?.kind === 'settlement' &&
                  selected.id === town.node.id,
              }
            }),
          ]}
        />
        {hover && (
          <Html position={[hover.x, 1.8, hover.z]} center zIndexRange={[20, 0]}>
            <div className='pointer-events-none rounded-md border bg-popover px-2 py-1 whitespace-nowrap text-popover-foreground shadow-sm'>
              {hover.text}
            </div>
          </Html>
        )}
      </Suspense>
    </SceneFrame>
  )
}

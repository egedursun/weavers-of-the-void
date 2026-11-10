import { type RefObject, useEffect, useMemo, useRef, useState } from 'react'
import { useFrame } from '@react-three/fiber'
import { Vector3 } from 'three'
import { type CosmosData, type CosmosWorld, type StarRecord } from '../api'
import { indexCosmos } from '../model/cosmosModel'
import { type Vec3, type WorldBody, layoutCosmos3D } from '../model/layout3d'
import { World3D } from './World3D'
import { createGeometries, disposeGeometries } from './geometries'
import { QUALITY_PRESETS } from './quality'
import {
  type FrameState,
  SceneContext,
  createFrameState,
  worldVector,
} from './sceneContext'

const MAX_STEP = 0.1

export type EmbeddedWorld = {
  id: number
  item: CosmosWorld
  body: WorldBody
  palette: string[]
  star: StarRecord | undefined
  starAt: Vec3 | null
  at: Vec3
}

function FrameClock({
  frameRef,
  worlds,
  radius,
  reduced,
}: {
  frameRef: RefObject<FrameState>
  worlds: readonly EmbeddedWorld[]
  radius: (world: EmbeddedWorld) => number
  reduced: boolean
}) {
  useFrame((_, delta) => {
    const frame = frameRef.current
    frame.reduced = reduced
    if (!reduced) frame.time += Math.min(delta, MAX_STEP)
    for (const world of worlds) {
      worldVector(frame, world.id).set(...world.at)
      frame.worldScale.set(
        world.id,
        radius(world) / Math.max(world.body.radius, 1e-6)
      )
    }
  })
  return null
}

export function EmbeddedWorlds3D({
  cosmos,
  worlds,
  radius,
  selectedId,
  reduced = false,
}: {
  cosmos: CosmosData
  worlds: readonly EmbeddedWorld[]
  radius: (world: EmbeddedWorld) => number
  selectedId: number | null
  reduced?: boolean
}) {
  const frameRef = useRef<FrameState>(createFrameState())
  const [labels] = useState(() => new Map<string, HTMLElement>())
  const preset = QUALITY_PRESETS.medium
  const index = useMemo(() => indexCosmos(cosmos), [cosmos])
  const layout = useMemo(() => layoutCosmos3D(cosmos), [cosmos])
  const geometries = useMemo(() => createGeometries(preset), [preset])
  useEffect(() => () => disposeGeometries(geometries), [geometries])
  const value = useMemo(
    () => ({
      frameRef,
      layout,
      index,
      preset,
      routeBend: new Map<number, number>(),
      geometries,
      labels,
    }),
    [layout, index, preset, geometries, labels]
  )
  const starPositions = useMemo(
    () =>
      new Map(
        worlds.flatMap((world) =>
          world.starAt
            ? [[world.id, new Vector3(...world.starAt)] as const]
            : []
        )
      ),
    [worlds]
  )
  return (
    <SceneContext.Provider value={value}>
      <FrameClock
        frameRef={frameRef}
        worlds={worlds}
        radius={radius}
        reduced={reduced}
      />
      {worlds.map((world) => (
        <World3D
          key={world.id}
          item={world.item}
          body={world.body}
          palette={world.palette}
          star={world.star}
          starPosition={starPositions.get(world.id)}
          god={undefined}
          selected={world.id === selectedId}
          hovered={false}
        />
      ))}
    </SceneContext.Provider>
  )
}

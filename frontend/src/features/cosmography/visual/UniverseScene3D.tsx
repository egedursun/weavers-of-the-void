import { Component, type ReactNode, useEffect, useMemo, useRef } from 'react'
import {
  Billboard,
  Line,
  OrbitControls,
  QuadraticBezierLine,
} from '@react-three/drei'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { DoubleSide, Euler, NeutralToneMapping, Vector3 } from 'three'
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib'
import { unitHash } from '@/lib/hash'
import { plural } from '@/lib/units'
import { type CosmosData } from '@/features/cosmos/api'
import { METHOD_LOOK } from '@/features/cosmos/model/looks'
import { EmbeddedWorlds3D } from '@/features/cosmos/scene3d/EmbeddedWorlds3D'
import { PostEffects3D } from '@/features/cosmos/scene3d/PostEffects3D'
import { shaderMaterial, uniform } from '@/features/cosmos/scene3d/materials'
import {
  type CosmographyCatalog,
  type GalaxyRecord,
  type RouteRecord,
  type StarRecord,
} from '../api'
import { type WorldMark, worldMarks, worldRadius } from '../galaxyWorlds'
import { type Ladder } from '../ladder'
import {
  CoreGlow,
  GalaxyParticles,
  StarMark,
  WorldMarker,
} from './GalaxyScene3D'
import { type SceneLabel, LabelLayer, LabelProjector } from './SceneLabels'
import { StarField } from './StarField'
import { ClockDriver, useTicking } from './clock'
import { DIMENSION_TOKEN } from './galaxyForm'
import { useLabelElements } from './labelElements'
import { scenePalette, tokenHex } from './palette'
import { CLOUD_FRAGMENT, PLANE_FRAGMENT, QUAD_VERTEX } from './shaders'
import {
  type PlacedGalaxy,
  type UniverseLayout,
  type Vec3,
  universeLayout,
} from './universeLayout'

export type ScalePick = {
  kind: 'dimension' | 'cluster' | 'galaxy'
  id: number
} | null

type UniverseProps = {
  ladder: Ladder
  catalog: CosmographyCatalog
  routes: readonly RouteRecord[]
  cosmos: CosmosData | undefined
  selected: ScalePick
  onPick: (pick: ScalePick) => void
  onOpen: (kind: 'star' | 'world', id: number) => void
  fallback: ReactNode
}

type Held = { stars: StarRecord[]; worlds: WorldMark[] }

const NAMED_INSIDE = 12

function heldIn(
  ladder: Ladder,
  cosmos: CosmosData | undefined
): Map<number, Held> {
  return new Map(
    ladder.data.galaxies.map((galaxy) => [
      galaxy.id,
      {
        stars: ladder.data.stars.filter((row) => row.galaxy_id === galaxy.id),
        worlds: worldMarks(cosmos, ladder.data, galaxy.id),
      },
    ])
  )
}

function bodySize(galaxy: GalaxyRecord): number {
  return Math.max(galaxy.radius * 0.06, 14)
}

function inSpace(
  placed: PlacedGalaxy,
  galaxy: GalaxyRecord,
  x: number,
  y: number
): Vec3 {
  const scale = placed.size / Math.max(galaxy.radius, 1)
  const point = new Vector3(x, 0, y)
    .applyEuler(new Euler(placed.tilt, placed.turn, 0))
    .multiplyScalar(scale)
  return [
    placed.position[0] + point.x,
    placed.position[1] + point.y,
    placed.position[2] + point.z,
  ]
}

const MINI_POINTS = 2600
const FOCUS_EASE = 0.06
const FOV = 45
const OPEN_RIFTS = new Set(['opening', 'open', 'closing'])

class Boundary extends Component<
  { fallback: ReactNode; children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  render() {
    return this.state.failed ? this.props.fallback : this.props.children
  }
}

function DimensionPlane({
  ladder,
  layout,
  id,
  selected,
  onPick,
}: {
  ladder: Ladder
  layout: UniverseLayout
  id: number
  selected: boolean
  onPick: (pick: ScalePick) => void
}) {
  const placed = layout.dimensions.get(id)
  const dimension = ladder.data.dimensions.find((row) => row.id === id)
  const token = dimension
    ? DIMENSION_TOKEN[dimension.dimension_kind]
    : '--dimension-prime'
  const material = useMemo(
    () =>
      shaderMaterial({
        vertex: QUAD_VERTEX,
        fragment: PLANE_FRAGMENT,
        uniforms: {
          uColor: uniform(scenePalette(token)),
          uAlpha: uniform(
            (selected ? 0.95 : 0.55) * (0.45 + (dimension?.veil ?? 50) / 180)
          ),
          uTime: uniform(0),
          uSeed: uniform(unitHash(`dimension-${id}`) * 50),
          uRings: uniform(6),
        },
        blend: 'additive',
        side: DoubleSide,
      }),
    [token, selected, dimension?.veil, id]
  )
  useEffect(() => () => material.dispose(), [material])
  useTicking(material)
  if (!placed || !dimension) return null
  return (
    <group position={[0, placed.y, 0]}>
      <mesh
        rotation={[-Math.PI / 2, 0, 0]}
        material={material}
        onClick={(event) => {
          event.stopPropagation()
          onPick({ kind: 'dimension', id })
        }}
      >
        <planeGeometry args={[placed.radius * 2, placed.radius * 2]} />
      </mesh>
    </group>
  )
}

function ClusterCloud({
  ladder,
  layout,
  id,
  selected,
  onPick,
}: {
  ladder: Ladder
  layout: UniverseLayout
  id: number
  selected: boolean
  onPick: (pick: ScalePick) => void
}) {
  const placed = layout.clusters.get(id)
  const cluster = ladder.data.clusters.find((row) => row.id === id)
  const material = useMemo(
    () =>
      shaderMaterial({
        vertex: QUAD_VERTEX,
        fragment: CLOUD_FRAGMENT,
        uniforms: {
          uColor: uniform(
            scenePalette(selected ? '--cosmos-copper' : '--galaxy-halo')
          ),
          uIntensity: uniform(selected ? 0.32 : 0.16),
          uSeed: uniform(unitHash(`cluster-${id}`) * 40),
          uTime: uniform(0),
        },
        blend: 'additive',
        side: DoubleSide,
      }),
    [selected, id]
  )
  useEffect(() => () => material.dispose(), [material])
  useTicking(material)
  if (!placed || !cluster) return null
  return (
    <group position={placed.position}>
      <mesh
        rotation={[-Math.PI / 2, 0, 0]}
        material={material}
        onClick={(event) => {
          event.stopPropagation()
          onPick({ kind: 'cluster', id })
        }}
      >
        <planeGeometry args={[placed.size * 2.2, placed.size * 2.2]} />
      </mesh>
      <Line
        points={Array.from({ length: 97 }, (_, index) => {
          const angle = (index / 96) * Math.PI * 2
          return [
            Math.cos(angle) * placed.size,
            0,
            Math.sin(angle) * placed.size,
          ] as Vec3
        })}
        color={tokenHex(selected ? '--cosmos-copper' : '--galaxy-halo')}
        lineWidth={selected ? 2 : 1.2}
        dashed
        dashSize={placed.size * 0.06}
        gapSize={placed.size * 0.04}
        transparent
        opacity={selected ? 0.95 : 0.6}
      />
    </group>
  )
}

function MiniGalaxy({
  ladder,
  catalog,
  layout,
  id,
  held,
  cosmos,
  selected,
  onPick,
  onOpen,
}: {
  ladder: Ladder
  catalog: CosmographyCatalog
  layout: UniverseLayout
  id: number
  held: Held | undefined
  cosmos: CosmosData | undefined
  selected: boolean
  onPick: (pick: ScalePick) => void
  onOpen: (kind: 'star' | 'world', id: number) => void
}) {
  const placed = layout.galaxies.get(id)
  const galaxy = ladder.data.galaxies.find((row) => row.id === id)
  if (!placed || !galaxy) return null
  const scale = placed.size / Math.max(galaxy.radius, 1)
  return (
    <group position={placed.position}>
      <group rotation={[placed.tilt, placed.turn, 0]} scale={scale}>
        <GalaxyParticles
          galaxy={galaxy}
          shape={catalog.shape}
          count={MINI_POINTS}
          attenuate={galaxy.radius * 4}
          brightness={selected ? 1.25 : 1}
        />
        <CoreGlow
          galaxy={galaxy}
          shape={catalog.shape}
          scale={selected ? 1.4 : 1}
        />
        {held?.stars.map((star) => (
          <StarMark
            key={star.id}
            star={star}
            size={bodySize(galaxy)}
            selected={false}
            onPick={(pick) => pick && onOpen('star', pick.id)}
          />
        ))}
        {cosmos && held && held.worlds.length > 0 && (
          <EmbeddedWorlds3D
            cosmos={cosmos}
            worlds={held.worlds}
            radius={() => worldRadius(bodySize(galaxy), false)}
            selectedId={null}
          />
        )}
        {held?.worlds.map((world) => (
          <WorldMarker
            key={world.id}
            world={world}
            size={bodySize(galaxy)}
            selected={false}
            onPick={(pick) => pick && onOpen('world', pick.id)}
          />
        ))}
      </group>
      <mesh
        visible={false}
        onClick={(event) => {
          event.stopPropagation()
          onPick({ kind: 'galaxy', id })
        }}
      >
        <sphereGeometry args={[placed.size, 16, 10]} />
      </mesh>
      {selected && (
        <Line
          points={Array.from({ length: 73 }, (_, index) => {
            const angle = (index / 72) * Math.PI * 2
            return [
              Math.cos(angle) * placed.size * 1.2,
              0,
              Math.sin(angle) * placed.size * 1.2,
            ] as Vec3
          })}
          color={tokenHex('--cosmos-copper')}
          lineWidth={1.5}
        />
      )}
    </group>
  )
}

function Links({ layout }: { layout: UniverseLayout }) {
  return (
    <group>
      {layout.links.map((link) => {
        const from = layout.galaxies.get(link.from)
        const to = layout.galaxies.get(link.to)
        if (!from || !to) return null
        const middle: Vec3 = [
          (from.position[0] + to.position[0]) / 2,
          Math.max(from.position[1], to.position[1]) +
            Math.hypot(
              from.position[0] - to.position[0],
              from.position[2] - to.position[2]
            ) *
              0.25 +
            60,
          (from.position[2] + to.position[2]) / 2,
        ]
        return (
          <QuadraticBezierLine
            key={link.key}
            start={from.position}
            end={to.position}
            mid={middle}
            color={tokenHex(METHOD_LOOK[link.method].token)}
            lineWidth={1 + Math.min(link.count, 4) * 0.6}
            dashed
            dashScale={0.04}
            transparent
            opacity={0.85}
          />
        )
      })}
    </group>
  )
}

function Rifts({ ladder, layout }: { ladder: Ladder; layout: UniverseLayout }) {
  const galaxyOfWorld = new Map(
    ladder.data.placements.map((row) => [row.world_id, row])
  )
  return (
    <group>
      {ladder.data.rifts
        .filter((rift) => OPEN_RIFTS.has(rift.state))
        .map((rift) => {
          const place = galaxyOfWorld.get(rift.world_id)
          const galaxy =
            place?.galaxy_id != null
              ? layout.galaxies.get(place.galaxy_id)
              : undefined
          const home =
            place?.dimension_id != null
              ? layout.dimensions.get(place.dimension_id)
              : undefined
          const target = layout.dimensions.get(rift.dimension_id)
          if (!target) return null
          const start: Vec3 = galaxy ? galaxy.position : [0, home?.y ?? 0, 0]
          const end: Vec3 = [start[0] * 0.6, target.y, start[2] * 0.6]
          return (
            <Line
              key={rift.id}
              points={[start, end]}
              color={tokenHex('--structure-rift')}
              lineWidth={2 + rift.size / 25}
              transparent
              opacity={0.9}
              dashed
              dashSize={40}
              gapSize={18}
            />
          )
        })}
    </group>
  )
}

function Beings({
  ladder,
  layout,
}: {
  ladder: Ladder
  layout: UniverseLayout
}) {
  return (
    <group>
      {ladder.data.beings
        .filter((being) => being.phase !== 'banished')
        .map((being) => {
          const galaxy =
            being.galaxy_id != null
              ? layout.galaxies.get(being.galaxy_id)
              : undefined
          const dimension =
            being.home_dimension_id != null
              ? layout.dimensions.get(being.home_dimension_id)
              : undefined
          const offset = unitHash(`being-${being.entity_id}`) * Math.PI * 2
          const base: Vec3 = galaxy
            ? [
                galaxy.position[0] + Math.cos(offset) * galaxy.size * 1.3,
                galaxy.position[1] + 60,
                galaxy.position[2] + Math.sin(offset) * galaxy.size * 1.3,
              ]
            : [
                Math.cos(offset) * 300,
                (dimension?.y ?? 0) + 80,
                Math.sin(offset) * 300,
              ]
          return (
            <group key={being.entity_id} position={base}>
              <Billboard>
                <mesh>
                  <circleGeometry args={[18, 24]} />
                  <meshBasicMaterial
                    color={tokenHex(
                      being.phase === 'incursion'
                        ? '--structure-rift'
                        : '--galaxy-leak'
                    )}
                    transparent
                    opacity={0.9}
                  />
                </mesh>
              </Billboard>
            </group>
          )
        })}
    </group>
  )
}

function Focus({ target }: { target: Vec3 | null }) {
  const controls = useThree(
    (state) => state.controls
  ) as OrbitControlsImpl | null
  const goal = useRef(new Vector3())
  const moving = useRef(false)
  useEffect(() => {
    if (!target) return
    goal.current.set(...target)
    moving.current = true
  }, [target])
  useFrame(() => {
    if (!controls || !moving.current) return
    controls.target.lerp(goal.current, FOCUS_EASE)
    controls.update()
    if (controls.target.distanceTo(goal.current) < 1) moving.current = false
  })
  return null
}

const WORLDS_NAMED = 3

function galaxyDetail(
  ladder: Ladder,
  catalog: CosmographyCatalog,
  galaxy: GalaxyRecord
): string {
  const kind =
    catalog.galaxy_types.find((row) => row.value === galaxy.galaxy_type)
      ?.label ?? galaxy.galaxy_type
  const worlds = ladder.data.placements
    .filter((row) => row.galaxy_id === galaxy.id)
    .map((row) => ladder.data.world_names[String(row.world_id)])
    .filter((name): name is string => name !== undefined)
  const stars = ladder.data.stars.filter(
    (row) => row.galaxy_id === galaxy.id
  ).length
  const held =
    worlds.length === 0
      ? 'no world'
      : worlds.length <= WORLDS_NAMED
        ? worlds.join(', ')
        : plural(worlds.length, 'world')
  return `${kind} · ${held} · ${plural(stars, 'star')}`
}

function universeLabels(
  ladder: Ladder,
  catalog: CosmographyCatalog,
  layout: UniverseLayout,
  held: Map<number, Held>,
  selected: ScalePick
): SceneLabel[] {
  const chosen = (kind: string, id: number) =>
    selected?.kind === kind && selected.id === id
  const labels: SceneLabel[] = []
  for (const dimension of ladder.data.dimensions) {
    const placed = layout.dimensions.get(dimension.id)
    if (!placed) continue
    const kind =
      catalog.dimension_kinds.find(
        (row) => row.value === dimension.dimension_kind
      )?.label ?? dimension.dimension_kind
    labels.push({
      key: `dimension-${dimension.id}`,
      position: [-placed.radius * 0.92, placed.y, placed.radius * 0.38],
      text: dimension.name,
      detail: `${kind} · time ×${dimension.time_factor}`,
      strong: chosen('dimension', dimension.id),
    })
  }
  for (const cluster of ladder.data.clusters) {
    const placed = layout.clusters.get(cluster.id)
    if (!placed) continue
    labels.push({
      key: `cluster-${cluster.id}`,
      position: [
        placed.position[0] - placed.size * 0.71,
        placed.position[1],
        placed.position[2] + placed.size * 0.71,
      ],
      text: cluster.name,
      detail: `${catalog.cluster_kinds.find((row) => row.value === cluster.cluster_kind)?.label ?? cluster.cluster_kind} · ${plural(ladder.galaxiesIn(cluster.id).length, 'galaxy', 'galaxies')}`,
      strong: chosen('cluster', cluster.id),
    })
  }
  for (const galaxy of ladder.data.galaxies) {
    const placed = layout.galaxies.get(galaxy.id)
    if (!placed) continue
    labels.push({
      key: `galaxy-${galaxy.id}`,
      position: [
        placed.position[0],
        placed.position[1] + placed.size * 0.55,
        placed.position[2],
      ],
      text: galaxy.name,
      detail: galaxyDetail(ladder, catalog, galaxy),
      strong: chosen('galaxy', galaxy.id),
    })
    const inside = held.get(galaxy.id)
    if (!inside) continue
    const count = inside.stars.length + inside.worlds.length
    if (count > NAMED_INSIDE && !chosen('galaxy', galaxy.id)) continue
    const lift = bodySize(galaxy) * (placed.size / Math.max(galaxy.radius, 1))
    for (const star of inside.stars)
      labels.push({
        key: `star-${star.id}`,
        position: inSpace(placed, galaxy, star.x, star.y).map((value, axis) =>
          axis === 1 ? value + lift : value
        ) as Vec3,
        text: star.name,
      })
    for (const world of inside.worlds)
      labels.push({
        key: `world-${world.id}`,
        position: inSpace(placed, galaxy, world.x, world.y).map(
          (value, axis) => (axis === 1 ? value - lift * 2.4 : value)
        ) as Vec3,
        text: world.name,
        quiet: true,
      })
  }
  for (const being of ladder.data.beings.filter(
    (row) => row.phase !== 'banished'
  )) {
    const galaxy =
      being.galaxy_id != null ? layout.galaxies.get(being.galaxy_id) : undefined
    const dimension =
      being.home_dimension_id != null
        ? layout.dimensions.get(being.home_dimension_id)
        : undefined
    const offset = unitHash(`being-${being.entity_id}`) * Math.PI * 2
    const base: Vec3 = galaxy
      ? [
          galaxy.position[0] + Math.cos(offset) * galaxy.size * 1.3,
          galaxy.position[1] + 94,
          galaxy.position[2] + Math.sin(offset) * galaxy.size * 1.3,
        ]
      : [
          Math.cos(offset) * 300,
          (dimension?.y ?? 0) + 114,
          Math.sin(offset) * 300,
        ]
    labels.push({
      key: `being-${being.entity_id}`,
      position: base,
      text: being.name,
    })
  }
  return labels
}

export default function UniverseScene3D({
  ladder,
  catalog,
  routes,
  cosmos,
  selected,
  onPick,
  onOpen,
  fallback,
}: UniverseProps) {
  const layout = useMemo(() => universeLayout(ladder, routes), [ladder, routes])
  const held = useMemo(() => heldIn(ladder, cosmos), [ladder, cosmos])
  const target = useMemo<Vec3 | null>(() => {
    if (!selected) return null
    if (selected.kind === 'galaxy')
      return layout.galaxies.get(selected.id)?.position ?? null
    if (selected.kind === 'cluster')
      return layout.clusters.get(selected.id)?.position ?? null
    const plane = layout.dimensions.get(selected.id)
    return plane ? [0, plane.y, 0] : null
  }, [selected, layout])
  const distance = layout.extent * 1.6
  const elements = useLabelElements()
  const labels = universeLabels(ladder, catalog, layout, held, selected)
  return (
    <Boundary fallback={fallback}>
      <div className='relative h-full w-full'>
        <Canvas
          aria-label='The heavens: dimensions, clusters and galaxies'
          dpr={[1, 2]}
          gl={{
            antialias: false,
            powerPreference: 'high-performance',
            stencil: false,
          }}
          camera={{
            fov: FOV,
            near: 1,
            far: 60000,
            position: [distance * 0.55, distance * 0.55, distance * 0.75],
          }}
          onCreated={({ gl }) => {
            gl.toneMapping = NeutralToneMapping
            gl.setClearColor(tokenHex('--cosmos-void'))
          }}
          onPointerMissed={() => onPick(null)}
        >
          <color attach='background' args={[tokenHex('--cosmos-void')]} />
          <StarField radius={layout.extent * 8} />
          {ladder.data.dimensions.map((row) => (
            <DimensionPlane
              key={row.id}
              ladder={ladder}
              layout={layout}
              id={row.id}
              selected={
                selected?.kind === 'dimension' && selected.id === row.id
              }
              onPick={onPick}
            />
          ))}
          {ladder.data.clusters.map((row) => (
            <ClusterCloud
              key={row.id}
              ladder={ladder}
              layout={layout}
              id={row.id}
              selected={selected?.kind === 'cluster' && selected.id === row.id}
              onPick={onPick}
            />
          ))}
          {ladder.data.galaxies.map((row) => (
            <MiniGalaxy
              key={row.id}
              ladder={ladder}
              catalog={catalog}
              layout={layout}
              id={row.id}
              held={held.get(row.id)}
              cosmos={cosmos}
              selected={selected?.kind === 'galaxy' && selected.id === row.id}
              onPick={onPick}
              onOpen={onOpen}
            />
          ))}
          <Links layout={layout} />
          <Rifts ladder={ladder} layout={layout} />
          <Beings ladder={ladder} layout={layout} />
          <OrbitControls
            makeDefault
            enableDamping
            minDistance={200}
            maxDistance={layout.extent * 6}
          />
          <Focus target={target} />
          <ClockDriver />
          <LabelProjector labels={labels} elements={elements} />
          <PostEffects3D samples={4} />
        </Canvas>
        <LabelLayer labels={labels} elements={elements} />
      </div>
    </Boundary>
  )
}

import {
  Component,
  type ReactNode,
  memo,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import { Billboard, Line, OrbitControls } from '@react-three/drei'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import {
  BufferAttribute,
  BufferGeometry,
  DoubleSide,
  NeutralToneMapping,
  Vector3,
} from 'three'
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib'
import { unitHash } from '@/lib/hash'
import { onTap } from '@/lib/sceneTap'
import { plural } from '@/lib/units'
import { PostEffects3D } from '@/features/cosmos/scene3d/PostEffects3D'
import { shaderMaterial, uniform } from '@/features/cosmos/scene3d/materials'
import {
  DUST_FRAGMENT,
  DUST_VERTEX,
} from '@/features/cosmos/scene3d/shaders/sky'
import {
  type CosmographyCatalog,
  type GalaxyRecord,
  type RouteRecord,
} from '../api'
import { type Ladder } from '../ladder'
import { CoreGlow, GalaxyParticles } from './GalaxyScene3D'
import { type SceneLabel, LabelLayer, LabelProjector } from './SceneLabels'
import { StarField } from './StarField'
import { ClockDriver, useTicking } from './clock'
import {
  CLUSTER_LOOK,
  type ClusterCloud as ClusterCloudPoints,
  clusterCloud,
  clusterOutline,
  clusterSkeleton,
  veilSpan,
} from './clusterForm'
import { DIMENSION_TOKEN } from './galaxyForm'
import { useLabelElements } from './labelElements'
import { scenePalette, tokenHex } from './palette'
import {
  CLOUD_FRAGMENT,
  PLANE_FRAGMENT,
  QUAD_VERTEX,
  SHELL_FRAGMENT,
} from './shaders'
import {
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
  selected: ScalePick
  onPick: (pick: ScalePick) => void
  fallback: ReactNode
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

const DimensionPlane = memo(function DimensionPlane({
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
        onClick={onTap(() => onPick({ kind: 'dimension', id }))}
      >
        <planeGeometry args={[placed.radius * 2, placed.radius * 2]} />
      </mesh>
    </group>
  )
})

const CLUSTER_POINTS_PER_GALAXY = 220
const CLUSTER_POINTS_MIN = 1200
const CLUSTER_POINTS_MAX = 6000
const CLUSTER_POINT_RATIO = 1.8
const CLUSTER_SELECTED_GLOW = 1.3
const CLUSTER_HAZE_STEP = 3
const CLUSTER_HAZE_SIZE = 8
const CLUSTER_HAZE_LIGHT = 0.05
const CLUSTER_REACH = 10
const CLUSTER_VEIL_BOOST = 1.8
const SKELETON_GLOW_WIDTH = 7
const SKELETON_GLOW_OPACITY = 0.18
const SKELETON_CORE_WIDTH = 1.6
const SKELETON_CORE_OPACITY = 0.38
const RIM_WIDTH = 4
const RIM_OPACITY = 0.12
const CLUSTER_VEIL_DROP = 6
const CLUSTER_HEAT_GLOW = 0.05
const CLUSTER_HEAT_SPAN = 0.55
const PERCENT = 100

function cloudGeometry(cloud: ClusterCloudPoints): BufferGeometry {
  const geometry = new BufferGeometry()
  geometry.setAttribute(
    'position',
    new BufferAttribute(cloud.positions.subarray(0, cloud.count * 3), 3)
  )
  geometry.setAttribute(
    'aColor',
    new BufferAttribute(cloud.colors.subarray(0, cloud.count * 3), 3)
  )
  geometry.setAttribute(
    'aSize',
    new BufferAttribute(cloud.sizes.subarray(0, cloud.count), 1)
  )
  geometry.setAttribute(
    'aSeed',
    new BufferAttribute(cloud.seeds.subarray(0, cloud.count), 1)
  )
  return geometry
}

function cloudHaze(cloud: ClusterCloudPoints): BufferGeometry {
  const count = Math.floor(cloud.count / CLUSTER_HAZE_STEP)
  const positions = new Float32Array(count * 3)
  const colors = new Float32Array(count * 3)
  const sizes = new Float32Array(count)
  const seeds = new Float32Array(count)
  for (let index = 0; index < count; index += 1) {
    const from = index * CLUSTER_HAZE_STEP
    positions.set(cloud.positions.subarray(from * 3, from * 3 + 3), index * 3)
    colors.set(
      Array.from(
        cloud.colors.subarray(from * 3, from * 3 + 3),
        (value) => value * CLUSTER_HAZE_LIGHT
      ),
      index * 3
    )
    sizes[index] = (cloud.sizes[from] ?? 1) * CLUSTER_HAZE_SIZE
    seeds[index] = cloud.seeds[from] ?? 0
  }
  const geometry = new BufferGeometry()
  geometry.setAttribute('position', new BufferAttribute(positions, 3))
  geometry.setAttribute('aColor', new BufferAttribute(colors, 3))
  geometry.setAttribute('aSize', new BufferAttribute(sizes, 1))
  geometry.setAttribute('aSeed', new BufferAttribute(seeds, 1))
  return geometry
}

const ClusterCloud = memo(function ClusterCloud({
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
  const shaped = useMemo(() => {
    const placed = layout.clusters.get(id)
    const cluster = ladder.data.clusters.find((row) => row.id === id)
    if (!placed || !cluster) return null
    const members = ladder.galaxiesIn(id).flatMap((galaxy) => {
      const spot = layout.galaxies.get(galaxy.id)
      return spot
        ? [
            {
              x: spot.position[0] - placed.position[0],
              y: spot.position[1] - placed.position[1],
              z: spot.position[2] - placed.position[2],
              size: spot.size,
            },
          ]
        : []
    })
    const cloud = clusterCloud(
      cluster.cluster_kind,
      members,
      placed.size,
      id,
      scenePalette,
      Math.min(
        Math.max(
          members.length * CLUSTER_POINTS_PER_GALAXY,
          CLUSTER_POINTS_MIN
        ),
        CLUSTER_POINTS_MAX
      )
    )
    return {
      placed,
      heat: cluster.medium_heat,
      look: CLUSTER_LOOK[cluster.cluster_kind],
      cloud,
      skeleton: clusterSkeleton(cluster.cluster_kind, members, cloud),
      rim: clusterOutline(cloud, cluster.cluster_kind),
    }
  }, [ladder, layout, id])
  const geometry = useMemo(
    () => (shaped ? cloudGeometry(shaped.cloud) : null),
    [shaped]
  )
  const haze = useMemo(
    () => (shaped ? cloudHaze(shaped.cloud) : null),
    [shaped]
  )
  const size = shaped?.placed.size ?? 1
  const dpr = useThree((state) => state.viewport.dpr)
  const material = useMemo(
    () =>
      shaderMaterial({
        vertex: DUST_VERTEX,
        fragment: DUST_FRAGMENT,
        uniforms: {
          uTime: uniform(0),
          uRatio: uniform(
            CLUSTER_POINT_RATIO * dpr * (selected ? CLUSTER_SELECTED_GLOW : 1)
          ),
          uAttenuate: uniform(size * CLUSTER_REACH),
        },
        blend: 'additive',
      }),
    [selected, size, dpr]
  )
  const veil = shaped?.cloud.veil ?? 'cloud'
  const body = shaped?.look.body ?? '--galaxy-halo'
  const intensity =
    (shaped?.look.haze ?? 0.12) *
    CLUSTER_VEIL_BOOST *
    (selected ? CLUSTER_SELECTED_GLOW : 1)
  const veilMaterial = useMemo(
    () =>
      shaderMaterial({
        vertex: QUAD_VERTEX,
        fragment: veil === 'shell' ? SHELL_FRAGMENT : CLOUD_FRAGMENT,
        uniforms: {
          uColor: uniform(scenePalette(body)),
          uIntensity: uniform(intensity),
          uSeed: uniform(unitHash(`cluster-${id}`) * 40),
          uTime: uniform(0),
        },
        blend: 'additive',
        side: DoubleSide,
      }),
    [veil, body, intensity, id]
  )
  const heat =
    ((shaped?.heat ?? 0) / PERCENT) *
    CLUSTER_HEAT_GLOW *
    (selected ? CLUSTER_SELECTED_GLOW : 1)
  const heatMaterial = useMemo(
    () =>
      shaderMaterial({
        vertex: QUAD_VERTEX,
        fragment: CLOUD_FRAGMENT,
        uniforms: {
          uColor: uniform(scenePalette('--structure-emission')),
          uIntensity: uniform(heat),
          uSeed: uniform(unitHash(`cluster-heat-${id}`) * 40),
          uTime: uniform(0),
        },
        blend: 'additive',
        side: DoubleSide,
      }),
    [heat, id]
  )
  useEffect(() => () => geometry?.dispose(), [geometry])
  useEffect(() => () => haze?.dispose(), [haze])
  useEffect(() => () => material.dispose(), [material])
  useEffect(() => () => veilMaterial.dispose(), [veilMaterial])
  useEffect(() => () => heatMaterial.dispose(), [heatMaterial])
  useTicking(material)
  useTicking(veilMaterial)
  useTicking(heatMaterial)
  if (!shaped || !geometry || !haze) return null
  const { placed, cloud, look, skeleton, rim } = shaped
  const [width, depth] = veilSpan(cloud, cloud.veil)
  return (
    <group position={placed.position}>
      <group
        position={[
          cloud.centre[0],
          cloud.centre[1] - CLUSTER_VEIL_DROP,
          cloud.centre[2],
        ]}
        rotation={[0, -cloud.angle, 0]}
      >
        <mesh rotation={[-Math.PI / 2, 0, 0]} material={veilMaterial}>
          <planeGeometry args={[width, depth]} />
        </mesh>
        {heat > 0 && (
          <mesh rotation={[-Math.PI / 2, 0, 0]} material={heatMaterial}>
            <planeGeometry
              args={[width * CLUSTER_HEAT_SPAN, depth * CLUSTER_HEAT_SPAN]}
            />
          </mesh>
        )}
      </group>
      <points geometry={haze} material={material} />
      <points geometry={geometry} material={material} />
      <mesh
        visible={false}
        onClick={onTap(() => onPick({ kind: 'cluster', id }))}
      >
        <sphereGeometry args={[placed.size, 16, 10]} />
      </mesh>
      {skeleton.length >= 2 && (
        <>
          <Line
            points={skeleton}
            segments
            color={tokenHex(look.body)}
            lineWidth={SKELETON_GLOW_WIDTH}
            transparent
            opacity={SKELETON_GLOW_OPACITY}
            depthWrite={false}
          />
          <Line
            points={skeleton}
            segments
            color={tokenHex(look.glow)}
            lineWidth={SKELETON_CORE_WIDTH}
            transparent
            opacity={SKELETON_CORE_OPACITY}
            depthWrite={false}
          />
        </>
      )}
      {!selected && (
        <Line
          points={rim}
          color={tokenHex(look.body)}
          lineWidth={RIM_WIDTH}
          transparent
          opacity={RIM_OPACITY}
          depthWrite={false}
        />
      )}
      {selected && (
        <Line
          points={rim}
          color={tokenHex('--cosmos-copper')}
          lineWidth={1.6}
          dashed
          dashSize={placed.size * 0.05}
          gapSize={placed.size * 0.035}
          transparent
          opacity={0.9}
        />
      )}
    </group>
  )
})

const MiniGalaxy = memo(function MiniGalaxy({
  ladder,
  catalog,
  layout,
  id,
  selected,
  onPick,
}: {
  ladder: Ladder
  catalog: CosmographyCatalog
  layout: UniverseLayout
  id: number
  selected: boolean
  onPick: (pick: ScalePick) => void
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
      </group>
      <mesh
        visible={false}
        onClick={onTap(() => onPick({ kind: 'galaxy', id }))}
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
})

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
  const invalidate = useThree((state) => state.invalidate)
  const goal = useRef(new Vector3())
  const moving = useRef(false)
  useEffect(() => {
    if (!target) return
    goal.current.set(...target)
    moving.current = true
    invalidate()
  }, [target, invalidate])
  useFrame(() => {
    if (!controls || !moving.current) return
    controls.target.lerp(goal.current, FOCUS_EASE)
    controls.update()
    if (controls.target.distanceTo(goal.current) < 1) moving.current = false
    else invalidate()
  })
  return null
}

const IDLE_FRAME_MS = 1000 / 30

function IdleTicker() {
  const invalidate = useThree((state) => state.invalidate)
  useEffect(() => {
    const timer = window.setInterval(() => invalidate(), IDLE_FRAME_MS)
    return () => window.clearInterval(timer)
  }, [invalidate])
  return null
}

const WORLDS_NAMED = 3
const GALAXIES_PER_FRAME = 12

function useProgressive(total: number, step: number): number {
  const [shown, setShown] = useState(step)
  useEffect(() => {
    if (shown >= total) return
    const frame = requestAnimationFrame(() =>
      setShown((value) => Math.min(value + step, total))
    )
    return () => cancelAnimationFrame(frame)
  }, [shown, total, step])
  return Math.min(shown, total)
}

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
  const stars = ladder.starsIn(galaxy.id).length
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
      detail: chosen('galaxy', galaxy.id)
        ? galaxyDetail(ladder, catalog, galaxy)
        : undefined,
      strong: chosen('galaxy', galaxy.id),
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
  selected,
  onPick,
  fallback,
}: UniverseProps) {
  const layout = useMemo(() => universeLayout(ladder, routes), [ladder, routes])
  const revealed = useProgressive(
    ladder.data.galaxies.length,
    GALAXIES_PER_FRAME
  )
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
  const labels = universeLabels(ladder, catalog, layout, selected)
  return (
    <Boundary fallback={fallback}>
      <div className='relative h-full w-full'>
        <Canvas
          aria-label='The heavens: dimensions, clusters and galaxies'
          frameloop='demand'
          dpr={[1, 2]}
          gl={{
            antialias: false,
            powerPreference: 'high-performance',
            stencil: false,
          }}
          camera={{
            fov: FOV,
            near: 1,
            far: Math.max(60000, layout.extent * 24),
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
          {ladder.data.galaxies
            .filter(
              (row, index) =>
                index < revealed ||
                (selected?.kind === 'galaxy' && selected.id === row.id)
            )
            .map((row) => (
              <MiniGalaxy
                key={row.id}
                ladder={ladder}
                catalog={catalog}
                layout={layout}
                id={row.id}
                selected={selected?.kind === 'galaxy' && selected.id === row.id}
                onPick={onPick}
              />
            ))}
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
          <IdleTicker />
          <LabelProjector labels={labels} elements={elements} />
          <PostEffects3D samples={4} />
        </Canvas>
        <LabelLayer labels={labels} elements={elements} />
      </div>
    </Boundary>
  )
}

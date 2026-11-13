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
import { useLatest } from '@/features/cosmos/scene3d/useLatest'
import {
  type CosmographyCatalog,
  type GalaxyRecord,
  type RouteRecord,
} from '../api'
import { type Ladder } from '../ladder'
import {
  CosmicWeb,
  DeepSky,
  DimensionAura,
  DriftDust,
  NebulaBanks,
} from './CosmicBackdrop'
import { DimensionOrbs } from './DimensionOrbs'
import { CoreGlow, GalaxyParticles } from './GalaxyScene3D'
import { type SceneLabel, LabelLayer, LabelProjector } from './SceneLabels'
import { ClockDriver, useTicking } from './clock'
import {
  CLUSTER_LOOK,
  type ClusterCloud as ClusterCloudPoints,
  clusterCloud,
  clusterOutline,
  clusterSkeleton,
  veilSpan,
} from './clusterForm'
import { DIMENSION_ACCENTS, webStrands } from './cosmicWeb'
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
  dimensionAnchor,
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
  overview: number
  fallback: ReactNode
}

const MINI_POINTS = 2600
const FOCUS_EASE = 0.06
const FOV = 45
const OPEN_RIFTS = new Set(['opening', 'open', 'closing'])
const SKY_REACH = 10
const OPENING_VIEW = 2.3
const OPENING_SIDE = 0.42
const OPENING_HEIGHT = 0.78
const OPENING_FRONT = 0.62
const WIDE_ASPECT = 1.6
const HEAVENS_BLOOM = { strength: 0.7, radius: 0.22, threshold: 0.82 }

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
  const accent =
    DIMENSION_ACCENTS[id % DIMENSION_ACCENTS.length] ?? '--cosmos-violet'
  const material = useMemo(
    () =>
      shaderMaterial({
        vertex: QUAD_VERTEX,
        fragment: PLANE_FRAGMENT,
        uniforms: {
          uColor: uniform(scenePalette(token)),
          uAccent: uniform(scenePalette(accent)),
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
    [token, accent, selected, dimension?.veil, id]
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
      <DimensionAura
        placed={placed}
        token={token}
        accent={accent}
        selected={selected}
      />
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
              ? dimensionAnchor(layout, place.dimension_id)
              : null
          const target = dimensionAnchor(layout, rift.dimension_id)
          if (!target) return null
          const start: Vec3 = galaxy ? galaxy.position : (home ?? [0, 0, 0])
          const end: Vec3 = layout.orbs.has(rift.dimension_id)
            ? target
            : [start[0] * 0.6, target[1], start[2] * 0.6]
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
          const base = beingSpot(layout, being, galaxy, BEING_LIFT)
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

type FocusGoal = {
  key: string
  point: Vec3
  distance: number
  wide?: boolean
}

function narrowFit(aspect: number): number {
  return Math.max(1, WIDE_ASPECT / Math.max(aspect, 0.1))
}

function Focus({ goal }: { goal: FocusGoal | null }) {
  const controls = useThree(
    (state) => state.controls
  ) as OrbitControlsImpl | null
  const camera = useThree((state) => state.camera)
  const invalidate = useThree((state) => state.invalidate)
  const aspect = useThree(
    (state) => state.size.width / Math.max(state.size.height, 1)
  )
  const fitted = useRef(false)
  const aim = useRef(new Vector3())
  const place = useRef(new Vector3())
  const moving = useRef(false)
  const latest = useLatest(goal)
  const key = goal?.key ?? null
  useEffect(() => {
    if (fitted.current || !controls) return
    fitted.current = true
    const away = camera.position.clone().sub(controls.target)
    camera.position
      .copy(controls.target)
      .addScaledVector(away, narrowFit(aspect))
    controls.update()
    invalidate()
  }, [controls, camera, aspect, invalidate])
  useEffect(() => {
    if (!controls) return
    const stop = () => {
      moving.current = false
    }
    controls.addEventListener('start', stop)
    return () => controls.removeEventListener('start', stop)
  }, [controls])
  useEffect(() => {
    const next = latest.current
    if (!controls || !next || key === null) return
    aim.current.set(...next.point)
    const away = camera.position.clone().sub(controls.target)
    if (away.lengthSq() === 0) away.set(0, 1, 1)
    place.current
      .copy(aim.current)
      .addScaledVector(
        away.normalize(),
        next.distance * (next.wide ? narrowFit(aspect) : 1)
      )
    moving.current = true
    invalidate()
  }, [key, latest, controls, camera, aspect, invalidate])
  useFrame(() => {
    if (!controls || !moving.current) return
    controls.target.lerp(aim.current, FOCUS_EASE)
    camera.position.lerp(place.current, FOCUS_EASE)
    controls.update()
    if (
      controls.target.distanceTo(aim.current) < 1 &&
      camera.position.distanceTo(place.current) < 1
    )
      moving.current = false
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

const BEING_LIFT = 60
const BEING_LABEL_LIFT = 94
const BEING_REACH = 1.3
const LOOSE_BEING_REACH = 300
const GALAXY_VIEW = 5
const CLUSTER_VIEW = 2.8
const ORB_VIEW = 16
const ORB_LABEL_LIFT = 2.4
const PLANE_VIEW = 1.7

function beingSpot(
  layout: UniverseLayout,
  being: Ladder['data']['beings'][number],
  galaxy: { position: Vec3; size: number } | undefined,
  lift: number
): Vec3 {
  const offset = unitHash(`being-${being.entity_id}`) * Math.PI * 2
  if (galaxy)
    return [
      galaxy.position[0] + Math.cos(offset) * galaxy.size * BEING_REACH,
      galaxy.position[1] + lift,
      galaxy.position[2] + Math.sin(offset) * galaxy.size * BEING_REACH,
    ]
  const orb =
    being.home_dimension_id != null
      ? layout.orbs.get(being.home_dimension_id)
      : undefined
  if (orb)
    return [
      orb.position[0] + Math.cos(offset) * orb.size * BEING_REACH,
      orb.position[1] + lift,
      orb.position[2] + Math.sin(offset) * orb.size * BEING_REACH,
    ]
  const plane =
    being.home_dimension_id != null
      ? layout.dimensions.get(being.home_dimension_id)
      : undefined
  return [
    Math.cos(offset) * LOOSE_BEING_REACH,
    (plane?.y ?? 0) + lift,
    Math.sin(offset) * LOOSE_BEING_REACH,
  ]
}

function focusGoal(
  layout: UniverseLayout,
  selected: ScalePick
): FocusGoal | null {
  if (!selected) return null
  const key = `${selected.kind}-${selected.id}`
  if (selected.kind === 'galaxy') {
    const placed = layout.galaxies.get(selected.id)
    return placed
      ? { key, point: placed.position, distance: placed.size * GALAXY_VIEW }
      : null
  }
  if (selected.kind === 'cluster') {
    const placed = layout.clusters.get(selected.id)
    return placed
      ? { key, point: placed.position, distance: placed.size * CLUSTER_VIEW }
      : null
  }
  const orb = layout.orbs.get(selected.id)
  if (orb) return { key, point: orb.position, distance: orb.size * ORB_VIEW }
  const plane = layout.dimensions.get(selected.id)
  return plane
    ? { key, point: [0, plane.y, 0], distance: plane.radius * PLANE_VIEW }
    : null
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
    const orb = layout.orbs.get(dimension.id)
    if (!placed && !orb) continue
    const kind =
      catalog.dimension_kinds.find(
        (row) => row.value === dimension.dimension_kind
      )?.label ?? dimension.dimension_kind
    labels.push({
      key: `dimension-${dimension.id}`,
      position: orb
        ? [
            orb.position[0],
            orb.position[1] + orb.size * ORB_LABEL_LIFT,
            orb.position[2],
          ]
        : placed
          ? [-placed.radius * 0.92, placed.y, placed.radius * 0.38]
          : [0, 0, 0],
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
    const base = beingSpot(layout, being, galaxy, BEING_LABEL_LIFT)
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
  overview,
  fallback,
}: UniverseProps) {
  const layout = useMemo(() => universeLayout(ladder, routes), [ladder, routes])
  const revealed = useProgressive(
    ladder.data.galaxies.length,
    GALAXIES_PER_FRAME
  )
  const planes = [...layout.dimensions.values()]
  const centre =
    planes.reduce((sum, plane) => sum + plane.y, 0) / Math.max(planes.length, 1)
  const goal = useMemo<FocusGoal | null>(
    () =>
      focusGoal(layout, selected) ??
      (overview > 0
        ? {
            key: `overview-${overview}`,
            point: [0, centre, 0],
            distance: layout.extent * OPENING_VIEW,
            wide: true,
          }
        : null),
    [selected, layout, overview, centre]
  )
  const distance = layout.extent * OPENING_VIEW
  const strands = useMemo(
    () =>
      webStrands(layout, (clusterId) => {
        const cluster = ladder.data.clusters.find((row) => row.id === clusterId)
        return cluster
          ? CLUSTER_LOOK[cluster.cluster_kind].body
          : '--galaxy-halo'
      }),
    [layout, ladder]
  )
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
            position: [
              distance * OPENING_SIDE,
              distance * OPENING_HEIGHT,
              distance * OPENING_FRONT,
            ],
          }}
          onCreated={({ gl }) => {
            gl.toneMapping = NeutralToneMapping
            gl.setClearColor(tokenHex('--cosmos-void'))
          }}
          onPointerMissed={() => onPick(null)}
        >
          <color attach='background' args={[tokenHex('--cosmos-void')]} />
          <DeepSky radius={layout.extent * SKY_REACH} />
          <NebulaBanks extent={layout.extent} centre={centre} />
          <DriftDust extent={layout.extent} centre={centre} />
          <CosmicWeb strands={strands} extent={layout.extent} />
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
          <DimensionOrbs
            ladder={ladder}
            layout={layout}
            selectedId={selected?.kind === 'dimension' ? selected.id : null}
            onPick={onPick}
          />
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
          <Focus goal={goal} />
          <ClockDriver />
          <IdleTicker />
          <LabelProjector labels={labels} elements={elements} />
          <PostEffects3D samples={4} bloom={HEAVENS_BLOOM} />
        </Canvas>
        <LabelLayer labels={labels} elements={elements} />
      </div>
    </Boundary>
  )
}

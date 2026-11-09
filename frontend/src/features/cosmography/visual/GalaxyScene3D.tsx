import { Component, type ReactNode, useEffect, useMemo, useState } from 'react'
import { Billboard, Line, OrbitControls } from '@react-three/drei'
import { Canvas } from '@react-three/fiber'
import {
  AdditiveBlending,
  BufferAttribute,
  BufferGeometry,
  DoubleSide,
  NeutralToneMapping,
} from 'three'
import { unitHash } from '@/lib/hash'
import { STAR_LOOK } from '@/features/cosmos/model/looks'
import { PostEffects3D } from '@/features/cosmos/scene3d/PostEffects3D'
import { shaderMaterial, uniform } from '@/features/cosmos/scene3d/materials'
import {
  DUST_FRAGMENT,
  DUST_VERTEX,
} from '@/features/cosmos/scene3d/shaders/sky'
import { type StarRecord, type StructureRecord } from '../api'
import { type WorldMark } from '../galaxyWorlds'
import {
  type LabelElements,
  LabelLayer,
  LabelProjector,
  type SceneLabel,
} from './SceneLabels'
import { StarField } from './StarField'
import { ClockDriver, useTicking } from './clock'
import {
  type FormInput,
  type GalaxyPoints,
  type GalaxyShape,
  LAYOUT_STRUCTURES,
  STRUCTURE_LOOK,
  coreGlow,
  galaxyPoints,
  zoneRings,
} from './galaxyForm'
import { useLabelElements } from './labelElements'
import { scenePalette, tokenHex } from './palette'
import {
  CLOUD_FRAGMENT,
  CORE_FRAGMENT,
  DARK_DUST_FRAGMENT,
  DARK_DUST_VERTEX,
  DARK_FRAGMENT,
  QUAD_VERTEX,
  SHELL_FRAGMENT,
} from './shaders'

const FULL_POINTS = 26000
const PORTRAIT_POINTS = 12000
const RING_SEGMENTS = 96
const FOV = 42
const POINT_RATIO = 1.6

export type Pick = { kind: 'star' | 'structure' | 'world'; id: number } | null

export type GalaxySceneProps = {
  galaxy: FormInput & { name: string }
  shape: GalaxyShape
  structures: readonly StructureRecord[]
  stars: readonly StarRecord[]
  worlds?: readonly WorldMark[]
  selected?: Pick
  placing?: boolean
  portrait?: boolean
  onPick?: (pick: Pick) => void
  onPlace?: (x: number, y: number) => void
  fallback: ReactNode
}

class SceneBoundary extends Component<
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

function geometryOf(points: GalaxyPoints, light: number): BufferGeometry {
  const geometry = new BufferGeometry()
  const colors = points.colors.slice(0, points.count * 3)
  if (light !== 1)
    for (let index = 0; index < colors.length; index += 1)
      colors[index] *= light
  geometry.setAttribute(
    'position',
    new BufferAttribute(points.positions.subarray(0, points.count * 3), 3)
  )
  geometry.setAttribute('aColor', new BufferAttribute(colors, 3))
  geometry.setAttribute(
    'aSize',
    new BufferAttribute(points.sizes.subarray(0, points.count), 1)
  )
  geometry.setAttribute(
    'aSeed',
    new BufferAttribute(points.seeds.subarray(0, points.count), 1)
  )
  return geometry
}

const HAZE_STEP = 5
const HAZE_SIZE = 7
const HAZE_LIGHT = 0.09

function hazeOf(points: GalaxyPoints, light: number): BufferGeometry {
  const count = Math.floor(points.count / HAZE_STEP)
  const positions = new Float32Array(count * 3)
  const colors = new Float32Array(count * 3)
  const sizes = new Float32Array(count)
  const seeds = new Float32Array(count)
  for (let index = 0; index < count; index += 1) {
    const from = index * HAZE_STEP
    positions.set(points.positions.subarray(from * 3, from * 3 + 3), index * 3)
    colors.set(
      [
        points.colors[from * 3] * HAZE_LIGHT * light,
        points.colors[from * 3 + 1] * HAZE_LIGHT * light,
        points.colors[from * 3 + 2] * HAZE_LIGHT * light,
      ],
      index * 3
    )
    sizes[index] = points.sizes[from] * HAZE_SIZE
    seeds[index] = points.seeds[from]
  }
  const geometry = new BufferGeometry()
  geometry.setAttribute('position', new BufferAttribute(positions, 3))
  geometry.setAttribute('aColor', new BufferAttribute(colors, 3))
  geometry.setAttribute('aSize', new BufferAttribute(sizes, 1))
  geometry.setAttribute('aSeed', new BufferAttribute(seeds, 1))
  return geometry
}

function darkGeometryOf(points: GalaxyPoints): BufferGeometry {
  const geometry = new BufferGeometry()
  geometry.setAttribute(
    'position',
    new BufferAttribute(points.dark.positions, 3)
  )
  geometry.setAttribute('aSize', new BufferAttribute(points.dark.sizes, 1))
  return geometry
}

export function GalaxyParticles({
  galaxy,
  shape,
  count,
  attenuate,
  brightness = 1,
  light = 1,
}: {
  galaxy: FormInput
  shape: GalaxyShape
  count: number
  attenuate: number
  brightness?: number
  light?: number
}) {
  const points = useMemo(
    () => galaxyPoints(galaxy, shape, count, scenePalette),
    [galaxy, shape, count]
  )
  const geometry = useMemo(() => geometryOf(points, light), [points, light])
  const haze = useMemo(() => hazeOf(points, light), [points, light])
  const dark = useMemo(() => darkGeometryOf(points), [points])
  const material = useMemo(
    () =>
      shaderMaterial({
        vertex: DUST_VERTEX,
        fragment: DUST_FRAGMENT,
        uniforms: {
          uTime: uniform(0),
          uRatio: uniform(POINT_RATIO * brightness),
          uAttenuate: uniform(attenuate),
        },
        blend: 'additive',
      }),
    [attenuate, brightness]
  )
  const darkMaterial = useMemo(
    () =>
      shaderMaterial({
        vertex: DARK_DUST_VERTEX,
        fragment: DARK_DUST_FRAGMENT,
        uniforms: {
          uRatio: uniform(POINT_RATIO * 2),
          uAttenuate: uniform(attenuate),
          uColor: uniform(scenePalette('--galaxy-dust')),
          uAlpha: uniform(0.35),
        },
        blend: 'normal',
      }),
    [attenuate]
  )
  useEffect(() => () => geometry.dispose(), [geometry])
  useEffect(() => () => haze.dispose(), [haze])
  useEffect(() => () => dark.dispose(), [dark])
  useEffect(() => () => material.dispose(), [material])
  useEffect(() => () => darkMaterial.dispose(), [darkMaterial])
  useTicking(material)
  return (
    <group>
      <points geometry={haze} material={material} />
      <points geometry={geometry} material={material} />
      {points.dark.count > 0 && (
        <points geometry={dark} material={darkMaterial} />
      )}
    </group>
  )
}

export function CoreGlow({
  galaxy,
  shape,
  scale = 1,
}: {
  galaxy: FormInput
  shape: GalaxyShape
  scale?: number
}) {
  const strength = coreGlow(galaxy)
  const material = useMemo(
    () =>
      shaderMaterial({
        vertex: QUAD_VERTEX,
        fragment: CORE_FRAGMENT,
        uniforms: {
          uColor: uniform(
            scenePalette(
              galaxy.nucleus === 'quasar' ? '--galaxy-quasar' : '--galaxy-core'
            )
          ),
          uEdge: uniform(scenePalette('--galaxy-bulge')),
          uStrength: uniform(Math.min(strength, 2) * 0.8 * scale),
          uTime: uniform(0),
        },
        blend: 'additive',
      }),
    [galaxy.nucleus, strength, scale]
  )
  useEffect(() => () => material.dispose(), [material])
  useTicking(material)
  const size = ((galaxy.radius * shape.bulge_reach_pct) / 100) * 1.7
  return (
    <Billboard>
      <mesh material={material}>
        <planeGeometry args={[size, size]} />
      </mesh>
    </Billboard>
  )
}

function StructureMark({
  structure,
  selected,
  onPick,
}: {
  structure: StructureRecord
  selected: boolean
  onPick?: (pick: Pick) => void
}) {
  const style = STRUCTURE_LOOK[structure.kind]
  const seed = unitHash(`structure-${structure.id}`) * 100
  const material = useMemo(() => {
    const color = scenePalette(style.token)
    const intensity = (0.25 + structure.intensity / 160) * (selected ? 1.6 : 1)
    if (style.form === 'dark')
      return shaderMaterial({
        vertex: QUAD_VERTEX,
        fragment: DARK_FRAGMENT,
        uniforms: {
          uColor: uniform(color),
          uIntensity: uniform(0.75),
          uSeed: uniform(seed),
        },
        blend: 'normal',
      })
    return shaderMaterial({
      vertex: QUAD_VERTEX,
      fragment: style.form === 'shell' ? SHELL_FRAGMENT : CLOUD_FRAGMENT,
      uniforms: {
        uColor: uniform(color),
        uIntensity: uniform(intensity),
        uSeed: uniform(seed),
        uTime: uniform(0),
      },
      blend: 'additive',
    })
  }, [style, structure.intensity, selected, seed])
  useEffect(() => () => material.dispose(), [material])
  useTicking(material)
  const size = Math.max(structure.radius * 2 * style.scale, 20)
  const cluster = style.form === 'cluster' || style.form === 'stream'
  const clusterGeometry = useMemo(() => {
    if (!cluster) return null
    const count = style.form === 'stream' ? 420 : 260
    const positions = new Float32Array(count * 3)
    const colors = new Float32Array(count * 3)
    const sizes = new Float32Array(count)
    const seeds = new Float32Array(count)
    const color = scenePalette(style.token)
    for (let index = 0; index < count; index += 1) {
      const t = index / count
      const a = unitHash(`${structure.id}-a-${index}`) * Math.PI * 2
      const r =
        Math.pow(
          unitHash(`${structure.id}-r-${index}`),
          style.form === 'stream' ? 1 : 2.2
        ) * structure.radius
      const x =
        style.form === 'stream'
          ? Math.cos(t * Math.PI * 1.2) * structure.radius * 1.4 +
            Math.cos(a) * r * 0.12
          : Math.cos(a) * r
      const z =
        style.form === 'stream'
          ? Math.sin(t * Math.PI * 1.2) * structure.radius * 0.6 +
            Math.sin(a) * r * 0.12
          : Math.sin(a) * r
      positions.set(
        [
          x,
          (unitHash(`${structure.id}-y-${index}`) - 0.5) *
            structure.radius *
            0.3,
          z,
        ],
        index * 3
      )
      const glow = 0.7 + unitHash(`${structure.id}-g-${index}`) * 0.6
      colors.set([color[0] * glow, color[1] * glow, color[2] * glow], index * 3)
      sizes[index] = 1.4 + unitHash(`${structure.id}-s-${index}`) * 1.6
      seeds[index] = unitHash(`${structure.id}-e-${index}`)
    }
    const geometry = new BufferGeometry()
    geometry.setAttribute('position', new BufferAttribute(positions, 3))
    geometry.setAttribute('aColor', new BufferAttribute(colors, 3))
    geometry.setAttribute('aSize', new BufferAttribute(sizes, 1))
    geometry.setAttribute('aSeed', new BufferAttribute(seeds, 1))
    return geometry
  }, [cluster, style, structure.id, structure.radius])
  const pointMaterial = useMemo(
    () =>
      shaderMaterial({
        vertex: DUST_VERTEX,
        fragment: DUST_FRAGMENT,
        uniforms: {
          uTime: uniform(0),
          uRatio: uniform(POINT_RATIO * 1.4),
          uAttenuate: uniform(structure.radius * 6),
        },
        blend: 'additive',
      }),
    [structure.radius]
  )
  useEffect(() => () => pointMaterial.dispose(), [pointMaterial])
  useEffect(() => () => clusterGeometry?.dispose(), [clusterGeometry])
  useTicking(pointMaterial)
  if (LAYOUT_STRUCTURES.has(structure.kind) || structure.ended_epoch !== null)
    return null
  return (
    <group position={[structure.x, 0, structure.y]}>
      {clusterGeometry ? (
        <points geometry={clusterGeometry} material={pointMaterial} />
      ) : (
        <Billboard>
          <mesh material={material}>
            <planeGeometry args={[size, size]} />
          </mesh>
        </Billboard>
      )}
      <mesh
        visible={false}
        onClick={(event) => {
          event.stopPropagation()
          onPick?.({ kind: 'structure', id: structure.id })
        }}
      >
        <sphereGeometry args={[Math.max(structure.radius, 18), 12, 8]} />
      </mesh>
    </group>
  )
}

function WorldMarker({
  world,
  size,
  selected,
  onPick,
}: {
  world: WorldMark
  size: number
  selected: boolean
  onPick?: (pick: Pick) => void
}) {
  const color = tokenHex(world.sunless ? '--cosmos-bone' : '--cosmos-orbit')
  const radius = size * (selected ? 0.32 : 0.2)
  return (
    <group position={[world.x, 0, world.y]}>
      <mesh
        onClick={(event) => {
          event.stopPropagation()
          onPick?.({ kind: 'world', id: world.id })
        }}
      >
        <sphereGeometry args={[radius, 16, 12]} />
        <meshBasicMaterial color={color} />
      </mesh>
      {selected && (
        <Line
          points={Array.from({ length: RING_SEGMENTS + 1 }, (_, index) => {
            const angle = (index / RING_SEGMENTS) * Math.PI * 2
            return [
              Math.cos(angle) * radius * 2,
              0,
              Math.sin(angle) * radius * 2,
            ] as [number, number, number]
          })}
          color={tokenHex('--cosmos-copper')}
          lineWidth={1.5}
          transparent
          opacity={0.9}
        />
      )}
    </group>
  )
}

function StarMark({
  star,
  selected,
  size,
  onPick,
}: {
  star: StarRecord
  selected: boolean
  size: number
  onPick?: (pick: Pick) => void
}) {
  const style = STAR_LOOK[star.star_type]
  const material = useMemo(
    () =>
      shaderMaterial({
        vertex: QUAD_VERTEX,
        fragment: CORE_FRAGMENT,
        uniforms: {
          uColor: uniform(scenePalette(style.lightToken)),
          uEdge: uniform(scenePalette(style.token)),
          uStrength: uniform(
            (0.6 + star.brightness / 120) * (selected ? 1.8 : 1)
          ),
          uTime: uniform(unitHash(`star-${star.id}`) * 10),
        },
        blend: 'additive',
      }),
    [style, star.brightness, star.id, selected]
  )
  useEffect(() => () => material.dispose(), [material])
  useTicking(material)
  const scale = size * (0.7 + style.size * 0.35) * (selected ? 1.5 : 1)
  return (
    <group position={[star.x, 0, star.y]}>
      <Billboard>
        <mesh
          material={material}
          onClick={(event) => {
            event.stopPropagation()
            onPick?.({ kind: 'star', id: star.id })
          }}
        >
          <planeGeometry args={[scale, scale]} />
        </mesh>
      </Billboard>
      {selected && (
        <Line
          points={Array.from({ length: RING_SEGMENTS + 1 }, (_, index) => {
            const angle = (index / RING_SEGMENTS) * Math.PI * 2
            return [
              Math.cos(angle) * scale * 0.7,
              0,
              Math.sin(angle) * scale * 0.7,
            ] as [number, number, number]
          })}
          color={tokenHex('--cosmos-copper')}
          lineWidth={1.5}
          transparent
          opacity={0.9}
        />
      )}
    </group>
  )
}

function ZoneRings({
  galaxy,
  shape,
}: {
  galaxy: FormInput
  shape: GalaxyShape
}) {
  const rings = useMemo(
    () => zoneRings(shape, galaxy.radius),
    [shape, galaxy.radius]
  )
  return (
    <group>
      {rings.map((ring) => (
        <group key={ring.key}>
          <Line
            points={Array.from({ length: RING_SEGMENTS + 1 }, (_, index) => {
              const angle = (index / RING_SEGMENTS) * Math.PI * 2
              return [
                Math.cos(angle) * ring.radius,
                0,
                Math.sin(angle) * ring.radius,
              ] as [number, number, number]
            })}
            color={tokenHex('--structure-frame')}
            lineWidth={1}
            dashed
            dashSize={ring.radius * 0.04}
            gapSize={ring.radius * 0.05}
            transparent
            opacity={0.18}
          />
        </group>
      ))}
    </group>
  )
}

function Placer({
  radius,
  onPlace,
}: {
  radius: number
  onPlace: (x: number, y: number) => void
}) {
  const [cursor, setCursor] = useState<[number, number] | null>(null)
  return (
    <group>
      <mesh
        rotation={[-Math.PI / 2, 0, 0]}
        onPointerMove={(event) => setCursor([event.point.x, event.point.z])}
        onPointerLeave={() => setCursor(null)}
        onClick={(event) => {
          event.stopPropagation()
          onPlace(Math.round(event.point.x), Math.round(event.point.z))
        }}
      >
        <circleGeometry args={[radius, 64]} />
        <meshBasicMaterial
          transparent
          opacity={0.04}
          color={tokenHex('--cosmos-copper')}
          side={DoubleSide}
          blending={AdditiveBlending}
          depthWrite={false}
        />
      </mesh>
      {cursor && (
        <Line
          points={Array.from({ length: 49 }, (_, index) => {
            const angle = (index / 48) * Math.PI * 2
            return [
              cursor[0] + Math.cos(angle) * radius * 0.05,
              1,
              cursor[1] + Math.sin(angle) * radius * 0.05,
            ] as [number, number, number]
          })}
          color={tokenHex('--cosmos-copper')}
          lineWidth={2}
        />
      )}
    </group>
  )
}

function Scene({
  galaxy,
  shape,
  structures,
  stars,
  worlds = [],
  selected = null,
  placing = false,
  portrait = false,
  onPick,
  onPlace,
  labels,
  elements,
}: Omit<GalaxySceneProps, 'fallback'> & {
  labels: readonly SceneLabel[]
  elements: LabelElements
}) {
  const halo = (galaxy.radius * shape.halo_reach_pct) / 100
  const starSize = Math.max(galaxy.radius * 0.045, 14)
  return (
    <>
      <StarField radius={galaxy.radius * 14} />
      <GalaxyParticles
        galaxy={galaxy}
        shape={shape}
        count={portrait ? PORTRAIT_POINTS : FULL_POINTS}
        attenuate={galaxy.radius * 2.2}
      />
      <CoreGlow galaxy={galaxy} shape={shape} />
      {!portrait && <ZoneRings galaxy={galaxy} shape={shape} />}
      {structures.map((structure) => (
        <StructureMark
          key={structure.id}
          structure={structure}
          selected={
            selected?.kind === 'structure' && selected.id === structure.id
          }
          onPick={onPick}
        />
      ))}
      {stars.map((star) => (
        <StarMark
          key={star.id}
          star={star}
          size={starSize}
          selected={selected?.kind === 'star' && selected.id === star.id}
          onPick={onPick}
        />
      ))}
      {worlds.map((world) => (
        <WorldMarker
          key={world.id}
          world={world}
          size={starSize}
          selected={selected?.kind === 'world' && selected.id === world.id}
          onPick={onPick}
        />
      ))}
      {placing && onPlace && <Placer radius={halo} onPlace={onPlace} />}
      <OrbitControls
        makeDefault
        enableDamping
        autoRotate={portrait || !selected}
        autoRotateSpeed={portrait ? 0.6 : 0.18}
        enableZoom={!portrait}
        enablePan={!portrait}
        minDistance={galaxy.radius * 0.25}
        maxDistance={galaxy.radius * 5}
        maxPolarAngle={Math.PI * 0.49}
      />
      <ClockDriver />
      <LabelProjector labels={labels} elements={elements} />
      <PostEffects3D samples={portrait ? 0 : 4} />
    </>
  )
}

function sceneLabels({
  galaxy,
  shape,
  structures,
  stars,
  worlds = [],
  selected = null,
  portrait = false,
}: GalaxySceneProps): SceneLabel[] {
  if (portrait) return []
  const starSize = Math.max(galaxy.radius * 0.045, 14)
  const shaped = structures.filter(
    (row) => !LAYOUT_STRUCTURES.has(row.kind) && row.ended_epoch === null
  )
  return [
    ...zoneRings(shape, galaxy.radius).map((ring) => ({
      key: `ring-${ring.key}`,
      position: [ring.radius * 0.71, 0, ring.radius * 0.71] as [
        number,
        number,
        number,
      ],
      text: ring.label,
      quiet: true,
    })),
    ...shaped
      .filter((row) =>
        selected?.kind === 'structure'
          ? selected.id === row.id
          : shaped.length <= 10
      )
      .map((row) => ({
        key: `structure-${row.id}`,
        position: [row.x, row.radius * 0.6 + 12, row.y] as [
          number,
          number,
          number,
        ],
        text: row.name,
      })),
    ...stars
      .filter(
        (row) =>
          stars.length <= 24 ||
          (selected?.kind === 'star' && selected.id === row.id)
      )
      .map((row) => ({
        key: `star-${row.id}`,
        position: [row.x, starSize * 0.6, row.y] as [number, number, number],
        text: row.name,
        strong: true,
      })),
    ...worlds
      .filter(
        (row) =>
          worlds.length <= 24 ||
          (selected?.kind === 'world' && selected.id === row.id)
      )
      .map((row) => ({
        key: `world-${row.id}`,
        position: [row.x, -starSize * 0.4, row.y] as [number, number, number],
        text: row.name,
        quiet: !(selected?.kind === 'world' && selected.id === row.id),
      })),
  ]
}

export default function GalaxyScene3D(props: GalaxySceneProps) {
  const distance = props.galaxy.radius * (props.portrait ? 2.1 : 1.9)
  const elements = useLabelElements()
  const labels = sceneLabels(props)
  return (
    <SceneBoundary fallback={props.fallback}>
      <div className='relative h-full w-full'>
        <Canvas
          aria-label={`Map of ${props.galaxy.name}`}
          dpr={[1, 2]}
          gl={{
            antialias: false,
            powerPreference: 'high-performance',
            stencil: false,
          }}
          camera={{
            fov: FOV,
            near: 1,
            far: props.galaxy.radius * 40,
            position: [0, distance * 0.62, distance * 0.78],
          }}
          onCreated={({ gl }) => {
            gl.toneMapping = NeutralToneMapping
            gl.setClearColor(tokenHex('--cosmos-void'))
          }}
          onPointerMissed={() => props.onPick?.(null)}
        >
          <color attach='background' args={[tokenHex('--cosmos-void')]} />
          <Scene {...props} labels={labels} elements={elements} />
        </Canvas>
        <LabelLayer labels={labels} elements={elements} />
      </div>
    </SceneBoundary>
  )
}

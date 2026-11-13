import { useEffect, useMemo, useRef } from 'react'
import { useFrame, useThree } from '@react-three/fiber'
import {
  BackSide,
  BufferAttribute,
  BufferGeometry,
  DoubleSide,
  type Group,
  type ShaderMaterial,
} from 'three'
import { seededRandom, unitHash } from '@/lib/hash'
import { DUST_TOKENS, NEBULA_TOKENS } from '@/features/cosmos/model/looks'
import {
  billboardMaterial,
  shaderMaterial,
  uniform,
} from '@/features/cosmos/scene3d/materials'
import {
  DUST_FRAGMENT,
  DUST_VERTEX,
  NEBULA_FRAGMENT,
  SKY_VERTEX,
} from '@/features/cosmos/scene3d/shaders/sky'
import { StarField } from './StarField'
import { useTicking } from './clock'
import { type WebStrand, webCloud } from './cosmicWeb'
import { scenePalette } from './palette'
import {
  CLOUD_FRAGMENT,
  CURTAIN_FRAGMENT,
  DEEP_SKY_FRAGMENT,
  FAR_GALAXY_FRAGMENT,
  FAR_GALAXY_VERTEX,
  FLARE_FRAGMENT,
  QUAD_VERTEX,
} from './shaders'
import { type PlacedDimension } from './universeLayout'

type Cloud = {
  positions: Float32Array
  colors: Float32Array
  sizes: Float32Array
  seeds: Float32Array
}

const SKY_SEGMENTS = 48
const SKY_STARS = 9000
const STAR_SHELL = 0.9
const FAR_GALAXIES = 340
const FAR_SHELL = 0.82
const FAR_SIZE_MIN = 5
const FAR_SIZE_RANGE = 16
const FLARES = 150
const FLARE_SHELL = 0.78
const FLARE_SIZE_MIN = 10
const FLARE_SIZE_RANGE = 22
const BAND_SHARE = 0.55
const BAND_TILT = 0.38
const BAND_SPREAD = 0.22
const DRIFT_POINTS = 3200
const DRIFT_REACH = 1.35
const DRIFT_THICKNESS = 0.3
const WEB_REACH = 1.6
const NEBULA_REACH_MIN = 0.9
const NEBULA_REACH_RANGE = 0.9
const NEBULA_LIFT_MIN = -0.5
const NEBULA_LIFT_RANGE = 0.7
const NEBULA_SIZE_MIN = 0.55
const NEBULA_SIZE_RANGE = 0.7
const NEBULA_LIGHT_MIN = 0.03
const NEBULA_LIGHT_RANGE = 0.035
const CURTAIN_HEIGHT = 0.2
const CURTAIN_DEPTH = 0.12
const CURTAIN_REACH = 0.985
const CURTAIN_SEGMENTS = 180
const CURTAIN_LIGHT = 0.55
const CURTAIN_SELECTED = 0.9
const MIRROR_LIGHT = 0.4
const UNDERGLOW_SPAN = 2.7
const UNDERGLOW_DROP = 0.08
const UNDERGLOW_LIGHT = 0.03

function pointsGeometry(cloud: Cloud, count: number): BufferGeometry {
  const geometry = new BufferGeometry()
  geometry.setAttribute(
    'position',
    new BufferAttribute(cloud.positions.subarray(0, count * 3), 3)
  )
  geometry.setAttribute(
    'aColor',
    new BufferAttribute(cloud.colors.subarray(0, count * 3), 3)
  )
  geometry.setAttribute(
    'aSize',
    new BufferAttribute(cloud.sizes.subarray(0, count), 1)
  )
  geometry.setAttribute(
    'aSeed',
    new BufferAttribute(cloud.seeds.subarray(0, count), 1)
  )
  return geometry
}

function skyShell(
  count: number,
  seed: number,
  radius: number,
  sizeMin: number,
  sizeRange: number,
  light: [number, number]
): BufferGeometry {
  const random = seededRandom(seed)
  const palette = DUST_TOKENS.map((token) => scenePalette(token))
  const cloud: Cloud = {
    positions: new Float32Array(count * 3),
    colors: new Float32Array(count * 3),
    sizes: new Float32Array(count),
    seeds: new Float32Array(count),
  }
  for (let index = 0; index < count; index += 1) {
    const theta = random() * Math.PI * 2
    let height = random() * 2 - 1
    if (random() < BAND_SHARE)
      height = -Math.sin(theta) * BAND_TILT + (random() - 0.5) * BAND_SPREAD
    const lean = Math.sqrt(Math.max(1 - height * height, 0))
    cloud.positions.set(
      [
        Math.cos(theta) * lean * radius,
        height * radius,
        Math.sin(theta) * lean * radius,
      ],
      index * 3
    )
    const color = palette[Math.floor(random() * palette.length)] ?? [1, 1, 1]
    const glow = light[0] + Math.pow(random(), 2) * light[1]
    cloud.colors.set(
      [color[0] * glow, color[1] * glow, color[2] * glow],
      index * 3
    )
    cloud.sizes[index] = sizeMin + Math.pow(random(), 3) * sizeRange
    cloud.seeds[index] = random()
  }
  return pointsGeometry(cloud, count)
}

function useDisposed(
  geometry: BufferGeometry | null,
  material: ShaderMaterial | null
) {
  useEffect(() => () => geometry?.dispose(), [geometry])
  useEffect(() => () => material?.dispose(), [material])
}

export function DeepSky({ radius }: { radius: number }) {
  const follow = useRef<Group>(null)
  const dpr = useThree((state) => state.viewport.dpr)
  const sky = useMemo(
    () =>
      shaderMaterial({
        vertex: SKY_VERTEX,
        fragment: DEEP_SKY_FRAGMENT,
        uniforms: {
          uBg: uniform(scenePalette('--cosmos-void')),
          uViolet: uniform(scenePalette('--cosmos-violet')),
          uTeal: uniform(scenePalette('--cosmos-teal')),
          uRose: uniform(scenePalette('--structure-emission')),
          uGold: uniform(scenePalette('--cosmos-copper')),
          uBone: uniform(scenePalette('--cosmos-bone')),
          uTime: uniform(0),
        },
        side: BackSide,
        depthWrite: false,
      }),
    []
  )
  const far = useMemo(
    () =>
      skyShell(
        FAR_GALAXIES,
        7741,
        radius * FAR_SHELL,
        FAR_SIZE_MIN,
        FAR_SIZE_RANGE,
        [0.18, 0.6]
      ),
    [radius]
  )
  const flares = useMemo(
    () =>
      skyShell(
        FLARES,
        90113,
        radius * FLARE_SHELL,
        FLARE_SIZE_MIN,
        FLARE_SIZE_RANGE,
        [0.35, 0.9]
      ),
    [radius]
  )
  const farMaterial = useMemo(
    () =>
      shaderMaterial({
        vertex: FAR_GALAXY_VERTEX,
        fragment: FAR_GALAXY_FRAGMENT,
        uniforms: { uRatio: uniform(dpr) },
        blend: 'additive',
      }),
    [dpr]
  )
  const flareMaterial = useMemo(
    () =>
      shaderMaterial({
        vertex: FAR_GALAXY_VERTEX,
        fragment: FLARE_FRAGMENT,
        uniforms: { uRatio: uniform(dpr) },
        blend: 'additive',
      }),
    [dpr]
  )
  useEffect(() => () => sky.dispose(), [sky])
  useDisposed(far, farMaterial)
  useDisposed(flares, flareMaterial)
  useTicking(sky)
  useFrame((state) => {
    follow.current?.position.copy(state.camera.position)
  })
  return (
    <group ref={follow}>
      <mesh material={sky} renderOrder={-10} frustumCulled={false}>
        <sphereGeometry args={[radius, SKY_SEGMENTS, SKY_SEGMENTS / 2]} />
      </mesh>
      <StarField radius={radius * STAR_SHELL} count={SKY_STARS} />
      <points geometry={far} material={farMaterial} frustumCulled={false} />
      <points
        geometry={flares}
        material={flareMaterial}
        frustumCulled={false}
      />
    </group>
  )
}

function dustMaterial(ratio: number, attenuate: number): ShaderMaterial {
  return shaderMaterial({
    vertex: DUST_VERTEX,
    fragment: DUST_FRAGMENT,
    uniforms: {
      uTime: uniform(0),
      uRatio: uniform(ratio),
      uAttenuate: uniform(attenuate),
    },
    blend: 'additive',
  })
}

export function CosmicWeb({
  strands,
  extent,
}: {
  strands: readonly WebStrand[]
  extent: number
}) {
  const dpr = useThree((state) => state.viewport.dpr)
  const geometry = useMemo(() => {
    const cloud = webCloud(strands, scenePalette)
    return cloud.count > 0 ? pointsGeometry(cloud, cloud.count) : null
  }, [strands])
  const material = useMemo(
    () => dustMaterial(dpr, extent * WEB_REACH),
    [dpr, extent]
  )
  useDisposed(geometry, material)
  useTicking(material)
  if (!geometry) return null
  return <points geometry={geometry} material={material} />
}

export function DriftDust({
  extent,
  centre,
}: {
  extent: number
  centre: number
}) {
  const dpr = useThree((state) => state.viewport.dpr)
  const geometry = useMemo(() => {
    const random = seededRandom(52711)
    const palette = DUST_TOKENS.map((token) => scenePalette(token))
    const cloud: Cloud = {
      positions: new Float32Array(DRIFT_POINTS * 3),
      colors: new Float32Array(DRIFT_POINTS * 3),
      sizes: new Float32Array(DRIFT_POINTS),
      seeds: new Float32Array(DRIFT_POINTS),
    }
    for (let index = 0; index < DRIFT_POINTS; index += 1) {
      const angle = random() * Math.PI * 2
      const reach = Math.sqrt(random()) * extent * DRIFT_REACH
      cloud.positions.set(
        [
          Math.cos(angle) * reach,
          centre + (random() - 0.5) * extent * DRIFT_THICKNESS,
          Math.sin(angle) * reach,
        ],
        index * 3
      )
      const color = palette[Math.floor(random() * palette.length)] ?? [1, 1, 1]
      const glow = 0.05 + Math.pow(random(), 4) * 0.7
      cloud.colors.set(
        [color[0] * glow, color[1] * glow, color[2] * glow],
        index * 3
      )
      cloud.sizes[index] = 1 + Math.pow(random(), 6) * 3
      cloud.seeds[index] = random()
    }
    return pointsGeometry(cloud, DRIFT_POINTS)
  }, [extent, centre])
  const material = useMemo(
    () => dustMaterial(dpr, extent * WEB_REACH),
    [dpr, extent]
  )
  useDisposed(geometry, material)
  useTicking(material)
  return <points geometry={geometry} material={material} />
}

function NebulaBank({
  token,
  slot,
  extent,
  centre,
}: {
  token: string
  slot: number
  extent: number
  centre: number
}) {
  const material = useMemo(() => {
    const made = billboardMaterial(NEBULA_FRAGMENT, {
      uColor: uniform(scenePalette(token)),
      uIntensity: uniform(
        NEBULA_LIGHT_MIN +
          unitHash(`heavens-nebula-i${slot}`) * NEBULA_LIGHT_RANGE
      ),
      uSeed: uniform(slot * 4.3 + 1.7),
      uTime: uniform(0),
    })
    made.uniforms.uSize.value =
      extent *
      (NEBULA_SIZE_MIN +
        unitHash(`heavens-nebula-s${slot}`) * NEBULA_SIZE_RANGE)
    return made
  }, [token, slot, extent])
  useEffect(() => () => material.dispose(), [material])
  useTicking(material)
  const angle = unitHash(`heavens-nebula-a${slot}`) * Math.PI * 2
  const reach =
    extent *
    (NEBULA_REACH_MIN +
      unitHash(`heavens-nebula-r${slot}`) * NEBULA_REACH_RANGE)
  const lift =
    extent *
    (NEBULA_LIFT_MIN + unitHash(`heavens-nebula-y${slot}`) * NEBULA_LIFT_RANGE)
  return (
    <mesh
      material={material}
      position={[
        Math.cos(angle) * reach,
        centre + lift,
        Math.sin(angle) * reach,
      ]}
      frustumCulled={false}
    >
      <planeGeometry args={[2, 2]} />
    </mesh>
  )
}

export function NebulaBanks({
  extent,
  centre,
}: {
  extent: number
  centre: number
}) {
  return (
    <group>
      {NEBULA_TOKENS.map((token, slot) => (
        <NebulaBank
          key={token}
          token={token}
          slot={slot}
          extent={extent}
          centre={centre}
        />
      ))}
    </group>
  )
}

function Curtain({
  radius,
  height,
  color,
  accent,
  light,
  seed,
  downward,
}: {
  radius: number
  height: number
  color: string
  accent: string
  light: number
  seed: number
  downward: boolean
}) {
  const material = useMemo(
    () =>
      shaderMaterial({
        vertex: QUAD_VERTEX,
        fragment: CURTAIN_FRAGMENT,
        uniforms: {
          uColor: uniform(scenePalette(color)),
          uAccent: uniform(scenePalette(accent)),
          uAlpha: uniform(light),
          uTime: uniform(0),
          uSeed: uniform(seed),
        },
        blend: 'additive',
        side: DoubleSide,
      }),
    [color, accent, light, seed]
  )
  useEffect(() => () => material.dispose(), [material])
  useTicking(material)
  return (
    <mesh
      material={material}
      position={[0, downward ? -height / 2 : height / 2, 0]}
      rotation={[downward ? Math.PI : 0, 0, 0]}
    >
      <cylinderGeometry
        args={[radius, radius, height, CURTAIN_SEGMENTS, 1, true]}
      />
    </mesh>
  )
}

export function DimensionAura({
  placed,
  token,
  accent,
  selected,
}: {
  placed: PlacedDimension
  token: string
  accent: string
  selected: boolean
}) {
  const seed = unitHash(`dimension-aura-${placed.id}`) * 40
  const glow = useMemo(
    () =>
      shaderMaterial({
        vertex: QUAD_VERTEX,
        fragment: CLOUD_FRAGMENT,
        uniforms: {
          uColor: uniform(scenePalette(token)),
          uIntensity: uniform(UNDERGLOW_LIGHT * (selected ? 1.5 : 1)),
          uSeed: uniform(seed),
          uTime: uniform(0),
        },
        blend: 'additive',
        side: DoubleSide,
      }),
    [token, selected, seed]
  )
  useEffect(() => () => glow.dispose(), [glow])
  useTicking(glow)
  const light = selected ? CURTAIN_SELECTED : CURTAIN_LIGHT
  const reach = placed.radius * CURTAIN_REACH
  return (
    <group>
      <Curtain
        radius={reach}
        height={placed.radius * CURTAIN_HEIGHT}
        color={token}
        accent={accent}
        light={light}
        seed={seed}
        downward={false}
      />
      <Curtain
        radius={reach}
        height={placed.radius * CURTAIN_DEPTH}
        color={token}
        accent={accent}
        light={light * MIRROR_LIGHT}
        seed={seed + 9}
        downward
      />
      <mesh
        material={glow}
        position={[0, -placed.radius * UNDERGLOW_DROP, 0]}
        rotation={[-Math.PI / 2, 0, 0]}
      >
        <planeGeometry
          args={[
            placed.radius * UNDERGLOW_SPAN,
            placed.radius * UNDERGLOW_SPAN,
          ]}
        />
      </mesh>
    </group>
  )
}

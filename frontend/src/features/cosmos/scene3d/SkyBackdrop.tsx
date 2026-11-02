import { useEffect, useMemo, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import {
  BackSide,
  BufferAttribute,
  BufferGeometry,
  Color,
  type Group,
  SphereGeometry,
} from 'three'
import { seededRandom, unitHash } from '../model/hash'
import { DUST_TOKENS, NEBULA_TOKENS } from '../model/looks'
import { billboardMaterial, shaderMaterial, uniform } from './materials'
import { tokenColor } from './sceneColors'
import { useScene } from './sceneContext'
import {
  DUST_FRAGMENT,
  DUST_VERTEX,
  NEBULA_FRAGMENT,
  SKY_FRAGMENT,
  SKY_VERTEX,
} from './shaders/sky'
import { useLatest } from './useLatest'

const DOME_RADIUS = 14000
const SHELL_POINTS = 7000
const SHELL_INNER = 9000
const SHELL_OUTER = 12500
const FAR_POINTS = 2600
const FAR_INNER = 2.2
const FAR_OUTER = 4.5
const DISC_POINTS = 2200
const DISC_REACH = 1.7
const DISC_THICKNESS = 0.5
const DISC_DROP = -40
const FLATTENED_SHARE = 0.38
const WHITE_LERP = 0.35
const NEBULA_HEIGHT_MIN = -160
const NEBULA_HEIGHT_RANGE = 260
const NEBULA_REACH_MIN = 0.35
const NEBULA_REACH_RANGE = 0.95
const NEBULA_SIZE_MIN = 0.9
const NEBULA_SIZE_RANGE = 1.1
const NEBULA_INTENSITY_MIN = 0.016
const NEBULA_INTENSITY_RANGE = 0.018
const DOME_SEGMENTS = 48

type DustShape = 'shell' | 'disc'

function dustGeometry(
  count: number,
  seed: number,
  shape: DustShape,
  inner: number,
  outer: number,
  thickness = 0
): BufferGeometry {
  const random = seededRandom(seed)
  const positions = new Float32Array(count * 3)
  const colors = new Float32Array(count * 3)
  const sizes = new Float32Array(count)
  const seeds = new Float32Array(count)
  const palette = DUST_TOKENS.map((token) => tokenColor(token))
  const white = new Color(1, 1, 1)
  const color = new Color()
  for (let index = 0; index < count; index += 1) {
    if (shape === 'shell') {
      const theta = random() * Math.PI * 2
      let cosPhi = random() * 2 - 1
      if (random() < FLATTENED_SHARE) cosPhi *= 0.25
      const sinPhi = Math.sqrt(1 - cosPhi * cosPhi)
      const radius = inner + random() * (outer - inner)
      positions.set(
        [
          Math.cos(theta) * sinPhi * radius,
          cosPhi * radius,
          Math.sin(theta) * sinPhi * radius,
        ],
        index * 3
      )
    } else {
      const angle = random() * Math.PI * 2
      const radius = Math.sqrt(random()) * outer
      positions.set(
        [
          Math.cos(angle) * radius,
          (random() - 0.5) * thickness,
          Math.sin(angle) * radius,
        ],
        index * 3
      )
    }
    const brightness = Math.pow(random(), 3.2) * 1.6 + 0.08
    color
      .copy(palette[Math.floor(random() * palette.length)])
      .lerp(white, WHITE_LERP * random())
      .multiplyScalar(brightness)
    colors.set([color.r, color.g, color.b], index * 3)
    sizes[index] = 1 + Math.pow(random(), 6) * 3.2
    seeds[index] = random()
  }
  const geometry = new BufferGeometry()
  geometry.setAttribute('position', new BufferAttribute(positions, 3))
  geometry.setAttribute('aColor', new BufferAttribute(colors, 3))
  geometry.setAttribute('aSize', new BufferAttribute(sizes, 1))
  geometry.setAttribute('aSeed', new BufferAttribute(seeds, 1))
  return geometry
}

function dustMaterial(ratio: number, attenuate: number) {
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

export function SkyBackdrop() {
  const { frameRef, preset, layout, geometries } = useScene()
  const dome = useMemo(() => {
    const geometry = new SphereGeometry(
      DOME_RADIUS,
      DOME_SEGMENTS,
      DOME_SEGMENTS / 2
    )
    const material = shaderMaterial({
      vertex: SKY_VERTEX,
      fragment: SKY_FRAGMENT,
      uniforms: {
        uBg: uniform(tokenColor('--cosmos-void')),
        uCopper: uniform(tokenColor('--cosmos-copper')),
        uViolet: uniform(tokenColor('--cosmos-violet')),
        uTeal: uniform(tokenColor('--cosmos-teal')),
        uBone: uniform(tokenColor('--cosmos-bone')),
      },
      side: BackSide,
      depthWrite: false,
    })
    const shell = dustGeometry(
      Math.round(SHELL_POINTS * preset.dust),
      16807,
      'shell',
      SHELL_INNER,
      SHELL_OUTER
    )
    return {
      geometry,
      material,
      shell,
      shellMaterial: dustMaterial(preset.pixelRatio, 0),
    }
  }, [preset])
  const extent = layout.extent
  const deep = useMemo(() => {
    const far = dustGeometry(
      Math.round(FAR_POINTS * preset.dust),
      48271,
      'shell',
      extent * FAR_INNER,
      extent * FAR_OUTER
    )
    const disc = dustGeometry(
      Math.round(DISC_POINTS * preset.dust),
      69621,
      'disc',
      0,
      extent * DISC_REACH,
      extent * DISC_THICKNESS
    )
    const nebulae = NEBULA_TOKENS.map((token, slot) => {
      const angle = unitHash(`nebula-a${slot}`) * Math.PI * 2
      const reach =
        extent *
        (NEBULA_REACH_MIN + unitHash(`nebula-r${slot}`) * NEBULA_REACH_RANGE)
      const material = billboardMaterial(NEBULA_FRAGMENT, {
        uColor: uniform(tokenColor(token)),
        uIntensity: uniform(
          NEBULA_INTENSITY_MIN +
            unitHash(`nebula-i${slot}`) * NEBULA_INTENSITY_RANGE
        ),
        uSeed: uniform(slot * 3.1),
        uTime: uniform(0),
      })
      material.uniforms.uSize.value =
        extent *
        (NEBULA_SIZE_MIN + unitHash(`nebula-s${slot}`) * NEBULA_SIZE_RANGE)
      return {
        key: token,
        material,
        position: [
          Math.cos(angle) * reach,
          NEBULA_HEIGHT_MIN - unitHash(`nebula-y${slot}`) * NEBULA_HEIGHT_RANGE,
          Math.sin(angle) * reach,
        ] as const,
      }
    })
    return {
      far,
      disc,
      nebulae,
      farMaterial: dustMaterial(preset.pixelRatio, 0),
      discMaterial: dustMaterial(preset.pixelRatio, extent),
    }
  }, [extent, preset])
  useEffect(
    () => () => {
      dome.geometry.dispose()
      dome.material.dispose()
      dome.shell.dispose()
      dome.shellMaterial.dispose()
    },
    [dome]
  )
  useEffect(
    () => () => {
      deep.far.dispose()
      deep.disc.dispose()
      deep.farMaterial.dispose()
      deep.discMaterial.dispose()
      for (const nebula of deep.nebulae) nebula.material.dispose()
    },
    [deep]
  )
  const follow = useRef<Group>(null)
  const skyRef = useLatest({ dome, deep })
  useFrame((state) => {
    const frame = frameRef.current
    const { dome: liveDome, deep: liveDeep } = skyRef.current
    if (follow.current) follow.current.position.copy(state.camera.position)
    for (const material of [
      liveDome.shellMaterial,
      liveDeep.farMaterial,
      liveDeep.discMaterial,
    ])
      material.uniforms.uTime.value = frame.time
    for (const material of liveDeep.nebulae.map((nebula) => nebula.material))
      material.uniforms.uTime.value = frame.time
  })
  return (
    <>
      <group ref={follow}>
        <mesh
          geometry={dome.geometry}
          material={dome.material}
          renderOrder={-10}
          frustumCulled={false}
        />
        <points
          geometry={dome.shell}
          material={dome.shellMaterial}
          renderOrder={-9}
          frustumCulled={false}
        />
      </group>
      <group position={layout.center}>
        <points
          geometry={deep.far}
          material={deep.farMaterial}
          frustumCulled={false}
        />
        <points
          geometry={deep.disc}
          material={deep.discMaterial}
          position={[0, DISC_DROP, 0]}
          frustumCulled={false}
        />
        {deep.nebulae.map((nebula) => (
          <mesh
            key={nebula.key}
            geometry={geometries.plane}
            material={nebula.material}
            position={nebula.position}
            frustumCulled={false}
          />
        ))}
      </group>
    </>
  )
}

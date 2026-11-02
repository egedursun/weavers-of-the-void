import { useEffect, useMemo, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import { type Group, type Mesh, type ShaderMaterial, Vector3 } from 'three'
import { type StarRecord } from '../api'
import { signedHash, unitHash } from '../model/hash'
import { type StarBody } from '../model/layout3d'
import { COMPANION_TOKENS, STAR_KIND_CODE, STAR_LOOK } from '../model/looks'
import { billboardMaterial, shaderMaterial, uniform } from './materials'
import { tokenColor } from './sceneColors'
import { useScene } from './sceneContext'
import {
  BEAM_FRAGMENT,
  BEAM_VERTEX,
  CORONA_FRAGMENT,
  DARK_HALO_FRAGMENT,
  DISK_FRAGMENT,
  DISK_VERTEX,
  STAR_FRAGMENT,
  STAR_VERTEX,
} from './shaders/star'
import { isDimStar } from './starLight'

const PERCENT = 100
const DIM_CORE = 0.7
const CORE_BASE = 0.95
const CORE_BRIGHT = 0.8
const CORONA_BASE = 2.3
const CORONA_BRIGHT = 2.2
const DARK_HALO = 6.4
const PHOTON_RING = 1.6
const REMNANT_SHELL = 16
const REBORN_SHOCK = 9
const TWIN_SEPARATION = 1.9
const TWIN_SPEED = 0.22
const BODY_SHARES: Record<number, readonly number[]> = {
  1: [0.56, 0.44],
  2: [0.5, 0.34, 0.3],
}
const BREATH_SPEED = 0.35
const BREATH_SWELL = 0.12
const MAGNETAR_FLICKER = 5.3
const SHARD_COUNT = 8
const SHARD_INNER = 1.28
const SHARD_SPREAD = 0.55
const BEAM_TILT = 0.42
const BEAM_SPIN = 1.6
const BEAM_LENGTH = 14
const PULSE_SPEED = 2.3
const DISK_TILT = 1.2

type Star3DProps = {
  star: StarRecord
  body: StarBody
  hovered: boolean
}

export function Star3D({ star, body, hovered }: Star3DProps) {
  const { geometries, frameRef } = useScene()
  const look = STAR_LOOK[star.star_type]
  const brightness = star.brightness / PERCENT
  const dim = isDimStar(star)
  const seed = unitHash(`star${star.id}`) * 10
  const coronaSize = CORONA_BASE + CORONA_BRIGHT * brightness
  const materials = useMemo(() => {
    const color = tokenColor(look.token)
    const edge = tokenColor(look.edgeToken)
    const coreIntensity = dim ? DIM_CORE : CORE_BASE + CORE_BRIGHT * brightness
    const core = shaderMaterial({
      vertex: STAR_VERTEX,
      fragment: STAR_FRAGMENT,
      uniforms: {
        uColor: uniform(color),
        uEdge: uniform(edge),
        uIntensity: uniform(coreIntensity),
        uTime: uniform(0),
        uSeed: uniform(seed),
        uKind: uniform(STAR_KIND_CODE[look.kind]),
        uPulse: uniform(0),
        uHover: uniform(0),
      },
    })
    const companions = Array.from({ length: look.companions }, (_, slot) =>
      shaderMaterial({
        vertex: STAR_VERTEX,
        fragment: STAR_FRAGMENT,
        uniforms: {
          uColor: uniform(
            tokenColor(COMPANION_TOKENS[slot % COMPANION_TOKENS.length])
          ),
          uEdge: uniform(edge),
          uIntensity: uniform(coreIntensity),
          uTime: uniform(0),
          uSeed: uniform(seed + 3 + slot),
          uKind: uniform(0),
          uPulse: uniform(0),
          uHover: uniform(0),
        },
      })
    )
    const shelled = look.kind === 'remnant' || look.shell
    const coronaMode = look.kind === 'black' ? 1 : shelled ? 2 : 0
    const coronaScale =
      look.kind === 'black' ? PHOTON_RING : shelled ? REMNANT_SHELL : coronaSize
    const corona = billboardMaterial(CORONA_FRAGMENT, {
      uColor: uniform(color),
      uIntensity: uniform(dim ? 0.45 : 0.75 + 0.5 * brightness),
      uTime: uniform(0),
      uSeed: uniform(seed),
      uCore: uniform(1 / coronaScale),
      uRays: uniform(look.rays),
      uSpike: uniform(look.spike),
      uMode: uniform(coronaMode),
      uPulse: uniform(0),
    })
    corona.uniforms.uSize.value = coronaScale
    const shock =
      look.kind === 'reborn'
        ? billboardMaterial(CORONA_FRAGMENT, {
            uColor: uniform(color),
            uIntensity: uniform(0.8),
            uTime: uniform(0),
            uSeed: uniform(seed),
            uCore: uniform(1 / REBORN_SHOCK),
            uRays: uniform(0),
            uSpike: uniform(0),
            uMode: uniform(3),
            uPulse: uniform(0),
          })
        : null
    if (shock) shock.uniforms.uSize.value = REBORN_SHOCK
    const dark =
      look.kind === 'black'
        ? billboardMaterial(
            DARK_HALO_FRAGMENT,
            { uCore: uniform(1 / DARK_HALO), uAlpha: uniform(0.92) },
            'normal'
          )
        : null
    if (dark) dark.uniforms.uSize.value = DARK_HALO
    const disk =
      look.kind === 'black'
        ? shaderMaterial({
            vertex: DISK_VERTEX,
            fragment: DISK_FRAGMENT,
            uniforms: {
              uInner: uniform(1.35),
              uOuter: uniform(3.9),
              uTime: uniform(0),
              uSeed: uniform(seed),
              uCenter: uniform(new Vector3(...body.position)),
              uNormal: uniform(new Vector3(0, 1, 0)),
              uIntensity: uniform(1.1),
            },
            blend: 'additive',
          })
        : null
    const beam =
      look.kind === 'pulse' || look.kind === 'magnetar'
        ? shaderMaterial({
            vertex: BEAM_VERTEX,
            fragment: BEAM_FRAGMENT,
            uniforms: { uColor: uniform(color), uIntensity: uniform(1.2) },
            blend: 'additive',
          })
        : null
    return { core, companions, corona, shock, dark, disk, beam }
  }, [look, dim, brightness, seed, coronaSize, body.position])
  useEffect(
    () => () => {
      for (const material of [
        materials.core,
        ...materials.companions,
        materials.corona,
        materials.shock,
        materials.dark,
        materials.disk,
        materials.beam,
      ])
        material?.dispose()
    },
    [materials]
  )
  const bodies = useRef<(Mesh | null)[]>([])
  const breath = useRef<Group>(null)
  const beams = useRef<Group>(null)
  const shards = useRef<Group>(null)
  useFrame(() => {
    const frame = frameRef.current
    const time = frame.time
    const pulse =
      look.kind === 'pulse'
        ? Math.pow(0.5 + 0.5 * Math.sin(time * PULSE_SPEED), 3)
        : look.kind === 'magnetar'
          ? Math.pow(
              0.5 +
                0.5 *
                  Math.sin(time * PULSE_SPEED) *
                  Math.sin(time * MAGNETAR_FLICKER),
              4
            )
          : look.kind === 'breathing'
            ? 0.5 + 0.5 * Math.sin(time * BREATH_SPEED)
            : 0
    const hover = hovered ? 1 : 0
    const list: (ShaderMaterial | null)[] = [
      materials.core,
      ...materials.companions,
      materials.corona,
      materials.shock,
      materials.disk,
    ]
    for (const material of list) {
      if (!material) continue
      if (material.uniforms.uTime) material.uniforms.uTime.value = time
      if (material.uniforms.uPulse) material.uniforms.uPulse.value = pulse
      if (material.uniforms.uHover) material.uniforms.uHover.value = hover
    }
    const count = bodies.current.length
    if (look.companions > 0) {
      const distance = body.radius * TWIN_SEPARATION
      const shares = BODY_SHARES[look.companions] ?? BODY_SHARES[1]
      bodies.current.forEach((mesh, slot) => {
        if (!mesh) return
        const angle = time * TWIN_SPEED + (slot / count) * Math.PI * 2
        const reach = distance * (1 - shares[slot])
        mesh.position.set(Math.cos(angle) * reach, 0, Math.sin(angle) * reach)
      })
    }
    if (breath.current && look.kind === 'breathing')
      breath.current.scale.setScalar(1 + BREATH_SWELL * (pulse - 0.5) * 2)
    if (beams.current) beams.current.rotation.y = time * BEAM_SPIN
    if (shards.current) shards.current.rotation.y = time * 0.05
  })
  const radius = body.radius
  const shardList = useMemo(
    () =>
      Array.from({ length: SHARD_COUNT }, (_, slot) => {
        const angle =
          (slot / SHARD_COUNT) * Math.PI * 2 + unitHash(`sh${star.id}${slot}`)
        const distance =
          SHARD_INNER + unitHash(`sd${star.id}${slot}`) * SHARD_SPREAD
        return {
          key: slot,
          position: [
            Math.cos(angle) * distance,
            signedHash(`sy${star.id}${slot}`) * 0.3,
            Math.sin(angle) * distance,
          ] as const,
          scale: 0.12 + unitHash(`ss${star.id}${slot}`) * 0.12,
        }
      }),
    [star.id]
  )
  return (
    <group position={body.position}>
      {materials.dark && (
        <mesh
          geometry={geometries.plane}
          material={materials.dark}
          scale={radius}
          renderOrder={-1}
          frustumCulled={false}
        />
      )}
      {look.companions > 0 ? (
        [materials.core, ...materials.companions].map((material, slot) => (
          <mesh
            key={slot}
            ref={(mesh) => {
              bodies.current[slot] = mesh
            }}
            geometry={geometries.sphere}
            material={material}
            scale={
              radius * (BODY_SHARES[look.companions] ?? BODY_SHARES[1])[slot]
            }
          />
        ))
      ) : (
        <group ref={breath}>
          <mesh
            geometry={geometries.sphere}
            material={materials.core}
            scale={radius}
          />
        </group>
      )}
      <mesh
        geometry={geometries.plane}
        material={materials.corona}
        scale={radius}
        frustumCulled={false}
      />
      {materials.shock && (
        <mesh
          geometry={geometries.plane}
          material={materials.shock}
          scale={radius}
          frustumCulled={false}
        />
      )}
      {materials.disk && (
        <mesh
          geometry={geometries.disk}
          material={materials.disk}
          scale={radius}
          rotation={[DISK_TILT, 0, 0.3]}
        />
      )}
      {materials.beam && (
        <group ref={beams}>
          <group rotation={[0, 0, BEAM_TILT]}>
            <mesh
              geometry={geometries.beam}
              material={materials.beam}
              scale={[radius * 0.9, radius * BEAM_LENGTH, radius * 0.9]}
            />
            <mesh
              geometry={geometries.beam}
              material={materials.beam}
              scale={[radius * 0.9, radius * BEAM_LENGTH, radius * 0.9]}
              rotation={[Math.PI, 0, 0]}
            />
          </group>
        </group>
      )}
      {look.kind === 'broken' && (
        <group ref={shards} scale={radius}>
          {shardList.map((shard) => (
            <mesh
              key={shard.key}
              geometry={geometries.shard}
              material={materials.core}
              position={shard.position}
              scale={shard.scale}
            />
          ))}
        </group>
      )}
    </group>
  )
}

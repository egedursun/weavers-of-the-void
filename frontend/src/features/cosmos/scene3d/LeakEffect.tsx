import { useEffect, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import { BufferAttribute, BufferGeometry } from 'three'
import { seededRandom } from '../model/hash'
import { billboardMaterial, shaderMaterial, uniform } from './materials'
import { tokenColor } from './sceneColors'
import { useScene } from './sceneContext'
import { LEAK_FRAGMENT, SPARK_FRAGMENT, SPARK_VERTEX } from './shaders/effects'
import { useLatest } from './useLatest'

export const LEAK_VISIBLE_FROM = 5
const PERCENT = 100
const HALO_BASE = 1.2
const HALO_GROWTH = 1.9
const STRENGTH_BASE = 0.12
const SPARKS_PER_POINT = 1.2

type LeakEffectProps = {
  worldId: number
  leakage: number
  radius: number
}

export function LeakEffect({ worldId, leakage, radius }: LeakEffectProps) {
  const { geometries, frameRef, preset } = useScene()
  const share = leakage / PERCENT
  const strength = Math.min(1, STRENGTH_BASE + share)
  const count = Math.round(leakage * SPARKS_PER_POINT)
  const halo = useMemo(() => {
    const material = billboardMaterial(
      LEAK_FRAGMENT,
      {
        uTime: uniform(0),
        uSeed: uniform(worldId * 1.37),
        uInner: uniform(1 / (HALO_BASE + share * HALO_GROWTH)),
        uStrength: uniform(strength),
        uDeep: uniform(tokenColor('--cosmos-leak')),
        uGlow: uniform(tokenColor('--cosmos-leak-glow')),
      },
      'premultiplied'
    )
    material.uniforms.uSize.value = HALO_BASE + share * HALO_GROWTH
    return material
  }, [worldId, share, strength])
  const sparks = useMemo(() => {
    const random = seededRandom(worldId * 7919 + 17)
    const directions = new Float32Array(count * 3)
    const seeds = new Float32Array(count)
    for (let index = 0; index < count; index += 1) {
      const theta = random() * Math.PI * 2
      const cosPhi = random() * 2 - 1
      const sinPhi = Math.sqrt(1 - cosPhi * cosPhi)
      directions.set(
        [Math.cos(theta) * sinPhi, cosPhi, Math.sin(theta) * sinPhi],
        index * 3
      )
      seeds[index] = random()
    }
    const geometry = new BufferGeometry()
    geometry.setAttribute(
      'position',
      new BufferAttribute(new Float32Array(count * 3), 3)
    )
    geometry.setAttribute('aDir', new BufferAttribute(directions, 3))
    geometry.setAttribute('aSeed', new BufferAttribute(seeds, 1))
    const material = shaderMaterial({
      vertex: SPARK_VERTEX,
      fragment: SPARK_FRAGMENT,
      uniforms: {
        uTime: uniform(0),
        uStrength: uniform(strength),
        uRatio: uniform(preset.pixelRatio),
        uGlow: uniform(tokenColor('--cosmos-leak-glow')),
      },
      blend: 'additive',
    })
    return { geometry, material }
  }, [worldId, count, strength, preset.pixelRatio])
  useEffect(
    () => () => {
      halo.dispose()
      sparks.geometry.dispose()
      sparks.material.dispose()
    },
    [halo, sparks]
  )
  const effectsRef = useLatest({ halo, sparks })
  useFrame(() => {
    const frame = frameRef.current
    const live = effectsRef.current
    live.halo.uniforms.uTime.value = frame.time
    live.sparks.material.uniforms.uTime.value = frame.time
  })
  return (
    <>
      <mesh
        geometry={geometries.plane}
        material={halo}
        scale={radius}
        frustumCulled={false}
      />
      <points
        geometry={sparks.geometry}
        material={sparks.material}
        scale={radius}
        frustumCulled={false}
      />
    </>
  )
}

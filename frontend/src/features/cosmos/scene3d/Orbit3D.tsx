import { useEffect, useMemo, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import { type Group } from 'three'
import { type WorldBody } from '../model/layout3d'
import { shaderMaterial, uniform } from './materials'
import { tokenColor } from './sceneColors'
import { useScene } from './sceneContext'
import { ORBIT_FRAGMENT, ORBIT_VERTEX } from './shaders/effects'
import { useLatest } from './useLatest'

const BASE_ALPHA = 0.085
const MISTY_ALPHA = 0.35
const LEGEND_ALPHA = 0.6
const FULL_TURN = Math.PI * 2

type Orbit3DProps = {
  body: WorldBody
  misty: boolean
  legend: boolean
  selected: boolean
}

export function Orbit3D({ body, misty, legend, selected }: Orbit3DProps) {
  const { geometries, frameRef } = useScene()
  const material = useMemo(
    () =>
      shaderMaterial({
        vertex: ORBIT_VERTEX,
        fragment: ORBIT_FRAGMENT,
        uniforms: {
          uColor: uniform(tokenColor('--cosmos-bone')),
          uTrail: uniform(tokenColor('--cosmos-copper')),
          uAlpha: uniform(
            BASE_ALPHA * (misty ? MISTY_ALPHA : legend ? LEGEND_ALPHA : 1)
          ),
          uPhase: uniform(0),
          uSelected: uniform(0),
        },
        blend: 'additive',
      }),
    [misty, legend]
  )
  useEffect(() => () => material.dispose(), [material])
  const materialRef = useLatest(material)
  const group = useRef<Group>(null)
  useFrame(() => {
    const frame = frameRef.current
    const live = materialRef.current
    const angle = body.phase + body.speed * frame.time
    live.uniforms.uPhase.value = (((angle / FULL_TURN) % 1) + 1) % 1
    live.uniforms.uSelected.value = selected ? 1 : 0
    if (!group.current) return
    if (body.kind === 'moon') {
      const parent = frame.worldPosition.get(body.parentId ?? 0)
      const scale = frame.worldScale.get(body.parentId ?? 0) ?? 1
      if (parent) group.current.position.copy(parent)
      group.current.scale.setScalar(body.orbitRadius * scale)
    } else {
      group.current.position.set(body.anchor[0], body.anchor[1], body.anchor[2])
      group.current.scale.setScalar(body.orbitRadius)
    }
  })
  if (body.kind === 'free') return null
  return (
    <group ref={group}>
      <group rotation={[body.inclination, body.node, 0, 'YXZ']}>
        <lineLoop
          geometry={geometries.orbit}
          material={material}
          frustumCulled={false}
        />
      </group>
    </group>
  )
}

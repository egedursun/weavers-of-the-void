import { useEffect, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import { type ForeignGodRecord } from '../api'
import { billboardMaterial, uniform } from './materials'
import { tokenColor } from './sceneColors'
import { useScene } from './sceneContext'
import { SEAL_FRAGMENT } from './shaders/effects'
import { sigilTexture } from './sigil'
import { useLatest } from './useLatest'

const SEAL_ALPHA = 0.09
const SEAL_SCALE = 4.9
const GAS_SEAL_SCALE = 7.2

type ForeignGodSealProps = {
  god: ForeignGodRecord
  radius: number
  gas: boolean
}

export function ForeignGodSeal({ god, radius, gas }: ForeignGodSealProps) {
  const { geometries, frameRef } = useScene()
  const hostile = god.stance < 0
  const material = useMemo(() => {
    const texture = sigilTexture(god.name)
    const seal = billboardMaterial(SEAL_FRAGMENT, {
      uMap: uniform(texture),
      uTime: uniform(0),
      uAlpha: uniform(SEAL_ALPHA),
      uColor: uniform(
        tokenColor(hostile ? '--cosmos-hostile' : '--cosmos-seal')
      ),
    })
    seal.uniforms.uSize.value = gas ? GAS_SEAL_SCALE : SEAL_SCALE
    return { seal, texture }
  }, [god.name, hostile, gas])
  useEffect(
    () => () => {
      material.seal.dispose()
      material.texture.dispose()
    },
    [material]
  )
  const materialRef = useLatest(material)
  useFrame(() => {
    const frame = frameRef.current
    materialRef.current.seal.uniforms.uTime.value = frame.time
  })
  return (
    <mesh
      geometry={geometries.plane}
      material={material.seal}
      scale={radius}
      frustumCulled={false}
    />
  )
}

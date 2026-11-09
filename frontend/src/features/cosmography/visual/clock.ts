import { useEffect } from 'react'
import { useFrame } from '@react-three/fiber'
import { type IUniform, type ShaderMaterial } from 'three'

const ticking = new Set<IUniform<number>>()

export function useTicking(material: ShaderMaterial) {
  useEffect(() => {
    const clock = material.uniforms.uTime as IUniform<number> | undefined
    if (!clock) return
    ticking.add(clock)
    return () => {
      ticking.delete(clock)
    }
  }, [material])
}

export function ClockDriver() {
  useFrame((state) => {
    for (const clock of ticking) clock.value = state.clock.elapsedTime
  })
  return null
}

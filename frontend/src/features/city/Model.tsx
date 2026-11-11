import { useMemo } from 'react'
import { useGLTF } from '@react-three/drei'
import { type ThreeEvent } from '@react-three/fiber'
import { Mesh } from 'three'
import { onTap } from '@/lib/sceneTap'
import { shared } from './materials'
import { type Part } from './models'

type ModelProps = {
  part: Part
  x: number
  z: number
  y?: number
  scale?: number
  tint?: string | null
  dim?: number
  onClick?: (event: ThreeEvent<MouseEvent>) => void
  onPointerOver?: (event: ThreeEvent<PointerEvent>) => void
  onPointerOut?: (event: ThreeEvent<PointerEvent>) => void
}

export function Model({
  part,
  x,
  z,
  y = 0,
  scale = 1,
  tint = null,
  dim = 1,
  onClick,
  onPointerOver,
  onPointerOut,
}: ModelProps) {
  const { scene } = useGLTF(part.model)
  const object = useMemo(() => {
    const copy = scene.clone(true)
    copy.traverse((child) => {
      if (child instanceof Mesh) {
        child.castShadow = true
        child.receiveShadow = true
        child.material = Array.isArray(child.material)
          ? child.material.map((item) => shared(item, tint, dim))
          : shared(child.material, tint, dim)
      }
    })
    return copy
  }, [scene, tint, dim])
  const [dx, dz] = part.offset ?? [0, 0]
  const size = (part.scale ?? 1) * scale
  return (
    <primitive
      object={object}
      position={[x + dx * scale, y, z + dz * scale]}
      rotation={[0, part.turn ?? 0, 0]}
      scale={[size, size, size]}
      onClick={onClick ? onTap(onClick) : undefined}
      onPointerOver={onPointerOver}
      onPointerOut={onPointerOut}
    />
  )
}

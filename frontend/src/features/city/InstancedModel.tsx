import { useLayoutEffect, useMemo, useRef } from 'react'
import { useGLTF } from '@react-three/drei'
import { type ThreeEvent } from '@react-three/fiber'
import {
  type InstancedMesh,
  type Material,
  Matrix4,
  Mesh,
  type Object3D,
  Quaternion,
  Vector3,
} from 'three'
import { onTap } from '@/lib/sceneTap'
import { shared } from './materials'

export type Placement = {
  x: number
  z: number
  y?: number
  scale?: number
  turn?: number
}

type Piece = { mesh: Mesh; local: Matrix4; material: Material | Material[] }

const UP = new Vector3(0, 1, 0)

function piecesOf(root: Object3D): Piece[] {
  root.updateMatrixWorld(true)
  const found: Piece[] = []
  root.traverse((child) => {
    if (child instanceof Mesh)
      found.push({
        mesh: child,
        local: child.matrixWorld.clone(),
        material: child.material,
      })
  })
  return found
}

function InstancedPiece<T extends Placement>({
  piece,
  items,
  tint,
  dim,
  bare,
  glow,
  onPick,
  onHover,
}: {
  piece: Piece
  items: T[]
  tint: string | null
  dim: number
  bare: boolean
  glow: boolean
  onPick?: (item: T) => void
  onHover?: (item: T | null) => void
}) {
  const ref = useRef<InstancedMesh>(null)
  const material = useMemo(
    () =>
      Array.isArray(piece.material)
        ? piece.material.map((item) => shared(item, tint, dim, bare, glow))
        : shared(piece.material, tint, dim, bare, glow),
    [piece.material, tint, dim, bare, glow]
  )
  useLayoutEffect(() => {
    const mesh = ref.current
    if (!mesh) return
    const placed = new Matrix4()
    const turn = new Quaternion()
    const size = new Vector3()
    const at = new Vector3()
    items.forEach((item, index) => {
      turn.setFromAxisAngle(UP, item.turn ?? 0)
      size.setScalar(item.scale ?? 1)
      at.set(item.x, item.y ?? 0, item.z)
      placed.compose(at, turn, size).multiply(piece.local)
      mesh.setMatrixAt(index, placed)
    })
    mesh.count = items.length
    mesh.instanceMatrix.needsUpdate = true
    mesh.computeBoundingSphere()
  }, [items, piece.local])
  return (
    <instancedMesh
      ref={ref}
      args={[piece.mesh.geometry, material, items.length]}
      castShadow
      receiveShadow
      onClick={
        onPick
          ? onTap((event: ThreeEvent<MouseEvent>) => {
              const item =
                event.instanceId !== undefined
                  ? items[event.instanceId]
                  : undefined
              if (item) onPick(item)
            })
          : undefined
      }
      onPointerOver={
        onHover
          ? (event: ThreeEvent<PointerEvent>) => {
              event.stopPropagation()
              onHover(
                event.instanceId !== undefined
                  ? (items[event.instanceId] ?? null)
                  : null
              )
            }
          : undefined
      }
      onPointerOut={onHover ? () => onHover(null) : undefined}
    />
  )
}

export function InstancedModel<T extends Placement>({
  model,
  items,
  tint = null,
  dim = 1,
  bare = false,
  glow = false,
  onPick,
  onHover,
}: {
  model: string
  items: T[]
  tint?: string | null
  dim?: number
  bare?: boolean
  glow?: boolean
  onPick?: (item: T) => void
  onHover?: (item: T | null) => void
}) {
  const { scene } = useGLTF(model)
  const pieces = useMemo(() => piecesOf(scene), [scene])
  if (items.length === 0) return null
  return (
    <>
      {pieces.map((piece, index) => (
        <InstancedPiece
          key={`${model}-${index}-${items.length}`}
          piece={piece}
          items={items}
          tint={tint}
          dim={dim}
          bare={bare}
          glow={glow}
          onPick={onPick}
          onHover={onHover}
        />
      ))}
    </>
  )
}

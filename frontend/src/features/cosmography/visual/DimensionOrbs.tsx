import { memo, useEffect, useMemo, useRef, useState } from 'react'
import { Line, useCursor } from '@react-three/drei'
import { useFrame } from '@react-three/fiber'
import { type Mesh, ShaderMaterial } from 'three'
import { onTap } from '@/lib/sceneTap'
import { billboardMaterial } from '@/features/cosmos/scene3d/materials'
import { useLatest } from '@/features/cosmos/scene3d/useLatest'
import { type Ladder } from '../ladder'
import { useTicking } from './clock'
import { dimensionUniforms } from './dimensionMaterial'
import { scenePalette, tokenHex } from './palette'
import { DIMENSION_FRAGMENT } from './shaders'
import {
  type PlacedOrb,
  type UniverseLayout,
  type Vec3,
  dimensionAnchor,
} from './universeLayout'

type Pick = { kind: 'dimension'; id: number }

const ORB_SPAN = 2.6
const HIT_REACH = 1.35
const HOVER_LIGHT = 1.35
const SELECTED_LIGHT = 1.2
const HOVER_RING = 0.5
const RING_POINTS = 160
const RING_OPACITY = 0.22
const TETHER_OPACITY = 0.35

const DimensionOrb = memo(function DimensionOrb({
  ladder,
  orb,
  selected,
  onPick,
}: {
  ladder: Ladder
  orb: PlacedOrb
  selected: boolean
  onPick: (pick: Pick) => void
}) {
  const [hovered, setHovered] = useState(false)
  useCursor(hovered)
  const dimension = ladder.data.dimensions.find((row) => row.id === orb.id)
  const kind = dimension?.dimension_kind ?? 'pocket'
  const veil = dimension?.veil ?? 50
  const stability = dimension?.stability ?? 50
  const magic = dimension?.magic ?? 0
  const time = dimension?.time_factor ?? 1
  const material = useMemo(() => {
    const made = billboardMaterial(
      DIMENSION_FRAGMENT,
      dimensionUniforms(
        { id: orb.id, kind, veil, stability, magic, time_factor: time },
        scenePalette,
        false
      )
    )
    made.uniforms.uSize.value = orb.size * ORB_SPAN
    return made
  }, [kind, veil, stability, magic, time, orb.id, orb.size])
  const mesh = useRef<Mesh>(null)
  const state = useLatest({ hovered, selected })
  useFrame(() => {
    const shader = mesh.current?.material
    if (!(shader instanceof ShaderMaterial)) return
    const { hovered: lit, selected: chosen } = state.current
    shader.uniforms.uLight.value = lit
      ? HOVER_LIGHT
      : chosen
        ? SELECTED_LIGHT
        : 1
    shader.uniforms.uRing.value = chosen ? 1 : lit ? HOVER_RING : 0
  })
  useEffect(() => () => material.dispose(), [material])
  useTicking(material)
  return (
    <group position={orb.position}>
      <mesh ref={mesh} material={material} frustumCulled={false}>
        <planeGeometry args={[2, 2]} />
      </mesh>
      <mesh
        visible={false}
        onClick={onTap(() => onPick({ kind: 'dimension', id: orb.id }))}
        onPointerOver={(event) => {
          event.stopPropagation()
          setHovered(true)
        }}
        onPointerOut={() => setHovered(false)}
      >
        <sphereGeometry args={[orb.size * HIT_REACH, 16, 12]} />
      </mesh>
    </group>
  )
})

function ringPoints(radius: number, y: number): Vec3[] {
  return Array.from({ length: RING_POINTS + 1 }, (_, index) => {
    const angle = (index / RING_POINTS) * Math.PI * 2
    return [Math.cos(angle) * radius, y, Math.sin(angle) * radius]
  })
}

export function DimensionOrbs({
  ladder,
  layout,
  selectedId,
  onPick,
}: {
  ladder: Ladder
  layout: UniverseLayout
  selectedId: number | null
  onPick: (pick: Pick) => void
}) {
  const tethers = [...layout.orbs.values()].flatMap((orb) => {
    const parent =
      orb.parentId !== null ? dimensionAnchor(layout, orb.parentId) : null
    return parent ? [{ key: orb.id, points: [orb.position, parent] }] : []
  })
  return (
    <group>
      {layout.rings.map((ring) => (
        <Line
          key={ring.radius}
          points={ringPoints(ring.radius, ring.y)}
          color={tokenHex('--cosmos-orbit')}
          lineWidth={1}
          dashed
          dashSize={ring.radius * 0.02}
          gapSize={ring.radius * 0.015}
          transparent
          opacity={RING_OPACITY}
          depthWrite={false}
        />
      ))}
      {tethers.map((tether) => (
        <Line
          key={tether.key}
          points={tether.points as [Vec3, Vec3]}
          color={tokenHex('--cosmos-leak-glow')}
          lineWidth={1.2}
          transparent
          opacity={TETHER_OPACITY}
          depthWrite={false}
        />
      ))}
      {[...layout.orbs.values()].map((orb) => (
        <DimensionOrb
          key={orb.id}
          ladder={ladder}
          orb={orb}
          selected={selectedId === orb.id}
          onPick={onPick}
        />
      ))}
    </group>
  )
}

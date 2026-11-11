import { Component, type ReactNode } from 'react'
import { OrbitControls } from '@react-three/drei'
import { Canvas } from '@react-three/fiber'
import { NeutralToneMapping } from 'three'
import { tokenHex } from '@/features/cosmography/visual/palette'

const FOV = 40

export class SceneBoundary extends Component<
  { fallback: ReactNode; children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  render() {
    return this.state.failed ? this.props.fallback : this.props.children
  }
}

export function SceneFrame({
  label,
  reach,
  fallback,
  children,
}: {
  label: string
  reach: number
  fallback: ReactNode
  children: ReactNode
}) {
  const far = Math.max(12, reach * 2.4)
  return (
    <SceneBoundary fallback={fallback}>
      <Canvas
        aria-label={label}
        shadows
        dpr={[1, 2]}
        camera={{
          fov: FOV,
          near: 0.1,
          far: far * 6,
          position: [far * 0.55, far * 0.75, far * 0.85],
        }}
        onCreated={({ gl }) => {
          gl.toneMapping = NeutralToneMapping
          gl.toneMappingExposure = 1.05
        }}
      >
        <hemisphereLight
          args={[tokenHex('--brand-gold-light'), tokenHex('--chart-2'), 0.9]}
        />
        <directionalLight
          castShadow
          position={[reach, reach * 2, reach * 0.6]}
          intensity={1.6}
          shadow-mapSize={[2048, 2048]}
        />
        <OrbitControls
          makeDefault
          enableDamping
          maxPolarAngle={Math.PI / 2.15}
          minDistance={3}
          maxDistance={far * 3}
        />
        {children}
      </Canvas>
    </SceneBoundary>
  )
}

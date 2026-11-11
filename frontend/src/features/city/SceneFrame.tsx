import { Component, type ReactNode } from 'react'
import { OrbitControls } from '@react-three/drei'
import { Canvas } from '@react-three/fiber'
import { NeutralToneMapping } from 'three'
import { tokenHex } from '@/features/cosmography/visual/palette'

const FOV = 38
const NEAREST = 1

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
  center = [0, 0],
  fallback,
  children,
}: {
  label: string
  reach: number
  center?: readonly [number, number]
  fallback: ReactNode
  children: ReactNode
}) {
  const span = Math.max(NEAREST, reach)
  const [cx, cz] = center
  const distance = span * 1.9
  const sky = tokenHex('--card')
  return (
    <SceneBoundary fallback={fallback}>
      <Canvas
        aria-label={label}
        shadows
        frameloop='demand'
        dpr={[1, 1.5]}
        performance={{ min: 0.6 }}
        camera={{
          fov: FOV,
          near: 0.1,
          far: distance * 8,
          position: [
            cx + distance * 0.55,
            distance * 0.95,
            cz + distance * 0.8,
          ],
        }}
        onCreated={({ gl }) => {
          gl.toneMapping = NeutralToneMapping
          gl.toneMappingExposure = 0.95
        }}
      >
        <color attach='background' args={[sky]} />
        <fog attach='fog' args={[sky, distance * 1.6, distance * 4]} />
        <hemisphereLight
          args={[
            tokenHex('--cosmos-bone'),
            tokenHex('--cosmos-void-edge'),
            1.1,
          ]}
        />
        <directionalLight
          castShadow
          position={[cx + span, span * 2.2, cz + span * 0.7]}
          intensity={1.6}
          color={tokenHex('--scene-sun')}
          shadow-mapSize={[1024, 1024]}
          shadow-camera-left={-span * 1.5}
          shadow-camera-right={span * 1.5}
          shadow-camera-top={span * 1.5}
          shadow-camera-bottom={-span * 1.5}
        />
        <OrbitControls
          makeDefault
          enableDamping
          target={[cx, 0, cz]}
          maxPolarAngle={Math.PI / 2.2}
          minDistance={1}
          maxDistance={distance * 3}
        />
        {children}
      </Canvas>
    </SceneBoundary>
  )
}

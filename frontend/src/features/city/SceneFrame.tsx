import { Component, type ReactNode } from 'react'
import { OrbitControls } from '@react-three/drei'
import { Canvas } from '@react-three/fiber'
import { NeutralToneMapping } from 'three'
import { tokenHex } from '@/features/cosmography/visual/palette'

const FOV = 38
const NEAREST = 1
const FULL_LIGHT = 100

export type SceneDepth = {
  light: number
  glow: string
  haze: string
  sky: string
  ambient: number
  near: number
  far: number
}

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
  depth = null,
}: {
  label: string
  reach: number
  center?: readonly [number, number]
  fallback: ReactNode
  children: ReactNode
  depth?: SceneDepth | null
}) {
  const span = Math.max(NEAREST, reach)
  const [cx, cz] = center
  const distance = span * 1.9
  const sky = depth ? depth.haze : tokenHex('--card')
  const lit = depth ? depth.light / FULL_LIGHT : 1
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
        <fog
          attach='fog'
          args={
            depth
              ? [sky, distance * depth.near, distance * depth.far]
              : [sky, distance * 1.6, distance * 4]
          }
        />
        <hemisphereLight
          args={[
            depth ? depth.sky : tokenHex('--cosmos-bone'),
            tokenHex('--cosmos-void-edge'),
            depth ? depth.ambient + lit * 0.7 : 1.1,
          ]}
        />
        {depth && (
          <pointLight
            position={[cx, span * 0.6, cz]}
            color={depth.glow}
            intensity={span * span * 0.6}
            distance={span * 1.8}
            decay={2}
          />
        )}
        <directionalLight
          castShadow
          position={[cx + span, span * 2.2, cz + span * 0.7]}
          intensity={depth ? 0.25 + lit * 1.2 : 1.6}
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

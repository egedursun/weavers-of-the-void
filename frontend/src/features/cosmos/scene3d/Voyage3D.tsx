import { useEffect, useMemo, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import { Color, type Mesh, type PerspectiveCamera, Vector3 } from 'three'
import { type JourneyRecord, type RouteRecord } from '../api'
import { METHOD_LOOK } from '../model/looks'
import { shaderMaterial, uniform } from './materials'
import { tokenColor } from './sceneColors'
import { useScene } from './sceneContext'
import { GLOW_FRAGMENT, VOYAGE_VERTEX } from './shaders/effects'
import { bezierAt, pixelsPerUnit } from './useCosmosFrame'
import { useLatest } from './useLatest'

const SPRITE_PIXELS = 11
const HOVER_GROWTH = 1.4
const WHITE_SHARE = 0.55
const BRIGHTNESS = 1.7
const TANGENT_STEP = 0.01

type Voyage3DProps = {
  journey: JourneyRecord
  route: RouteRecord
  hovered: boolean
}

export function Voyage3D({ journey, route, hovered }: Voyage3DProps) {
  const { geometries, frameRef } = useScene()
  const material = useMemo(() => {
    const color = tokenColor(METHOD_LOOK[route.method].token)
      .clone()
      .lerp(new Color(1, 1, 1), WHITE_SHARE)
      .multiplyScalar(BRIGHTNESS)
    return shaderMaterial({
      vertex: VOYAGE_VERTEX,
      fragment: GLOW_FRAGMENT,
      uniforms: {
        uSize: uniform(1),
        uAngle: uniform(0),
        uColor: uniform(color),
        uAlpha: uniform(1),
      },
      blend: 'additive',
    })
  }, [route.method])
  useEffect(() => () => material.dispose(), [material])
  const mesh = useRef<Mesh>(null)
  const materialRef = useLatest(material)
  useFrame((state) => {
    const frame = frameRef.current
    const live = materialRef.current
    const position = frame.voyagePosition.get(journey.id)
    const curve = frame.routeCurves.get(route.id)
    if (!mesh.current || !position || !curve) return
    mesh.current.position.copy(position)
    const camera = state.camera as PerspectiveCamera
    const distance = camera.position.distanceTo(position)
    live.uniforms.uSize.value =
      (SPRITE_PIXELS * (hovered ? HOVER_GROWTH : 1)) /
      pixelsPerUnit(camera, distance, frame.height)
    const towardB = journey.destination_world_id !== route.world_a_id
    const t = estimateT(curve.a, curve.c, curve.b, position)
    bezierAt(
      curve.a,
      curve.c,
      curve.b,
      Math.max(0, Math.min(1, t + (towardB ? TANGENT_STEP : -TANGENT_STEP))),
      next
    )
    here.copy(position).applyMatrix4(camera.matrixWorldInverse)
    next.applyMatrix4(camera.matrixWorldInverse)
    live.uniforms.uAngle.value =
      Math.atan2(next.y - here.y, next.x - here.x) - Math.PI / 2
  })
  return (
    <mesh
      ref={mesh}
      geometry={geometries.plane}
      material={material}
      frustumCulled={false}
      renderOrder={2}
    />
  )
}

const SAMPLES = 24
const sample = new Vector3()
const here = new Vector3()
const next = new Vector3()

function estimateT(
  a: Vector3,
  c: Vector3,
  b: Vector3,
  target: Vector3
): number {
  let best = 0
  let bestDistance = Infinity
  for (let step = 0; step <= SAMPLES; step += 1) {
    const t = step / SAMPLES
    const distance = bezierAt(a, c, b, t, sample).distanceToSquared(target)
    if (distance < bestDistance) {
      bestDistance = distance
      best = t
    }
  }
  return best
}

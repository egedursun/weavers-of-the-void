import { useEffect, useMemo, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import {
  AdditiveBlending,
  DoubleSide,
  type Group,
  MeshBasicMaterial,
  Vector2,
  Vector3,
} from 'three'
import { type RouteRecord } from '../api'
import { routeState } from '../model/cosmosModel'
import { unitHash } from '../model/hash'
import { METHOD_LOOK } from '../model/looks'
import { billboardMaterial, shaderMaterial, uniform } from './materials'
import { tokenColor } from './sceneColors'
import { useScene } from './sceneContext'
import {
  ROUTE_FRAGMENT,
  ROUTE_VERTEX,
  VORTEX_FRAGMENT,
} from './shaders/effects'
import { bezierAt } from './useCosmosFrame'
import { useLatest } from './useLatest'

const PERCENT = 100
const WIDTH_BASE = 1.15
const WIDTH_DANGER = 0.45
const GLOW_BASE = 1.25
const GLOW_DANGER = 0.6
const CLOSED_ALPHA = 0.14
const UNKNOWN_ALPHA = 0.38
const HOVER_EASE = 10
const PORTAL_GAP = 2.4
const PORTAL_SCALE = 1.6
const point = new Vector3()
const ahead = new Vector3()

type Route3DProps = {
  route: RouteRecord
  hovered: boolean
  highlighted: boolean
}

export function Route3D({ route, hovered, highlighted }: Route3DProps) {
  const { geometries, frameRef, layout } = useScene()
  const look = METHOD_LOOK[route.method]
  const state = routeState(route)
  const danger = route.danger / PERCENT
  const material = useMemo(
    () =>
      shaderMaterial({
        vertex: ROUTE_VERTEX,
        fragment: ROUTE_FRAGMENT,
        uniforms: {
          uA: uniform(new Vector3()),
          uB: uniform(new Vector3()),
          uC: uniform(new Vector3()),
          uResolution: uniform(new Vector2(1, 1)),
          uWidth: uniform(look.ribbon * (WIDTH_BASE - danger * WIDTH_DANGER)),
          uTime: uniform(0),
          uStyle: uniform(look.style),
          uHover: uniform(0),
          uColor: uniform(tokenColor(look.token)),
          uIntensity: uniform(look.glow * (GLOW_BASE - danger * GLOW_DANGER)),
          uLength: uniform(1),
          uAlpha: uniform(
            !state.open ? CLOSED_ALPHA : route.known ? 1 : UNKNOWN_ALPHA
          ),
          uSeed: uniform(unitHash(`route${route.id}`) * 10),
          uFlow: uniform(state.open ? 1 : 0),
        },
        blend: 'premultiplied',
        side: DoubleSide,
      }),
    [look, danger, state.open, route.known, route.id]
  )
  const vortex = useMemo(() => {
    if (!look.endRings) return null
    const swirl = billboardMaterial(VORTEX_FRAGMENT, {
      uColor: uniform(tokenColor(look.token)),
      uTime: uniform(0),
      uAlpha: uniform(state.open ? 1 : CLOSED_ALPHA),
      uSeed: uniform(route.id * 0.31),
    })
    swirl.uniforms.uSize.value = 0.9
    return swirl
  }, [look, state.open, route.id])
  const ringMaterial = useMemo(
    () =>
      look.endRings
        ? new MeshBasicMaterial({
            color: tokenColor(look.token),
            transparent: true,
            opacity: state.open ? 0.8 : CLOSED_ALPHA,
            blending: AdditiveBlending,
            depthWrite: false,
          })
        : null,
    [look, state.open]
  )
  useEffect(
    () => () => {
      material.dispose()
      vortex?.dispose()
      ringMaterial?.dispose()
    },
    [material, vortex, ringMaterial]
  )
  const hover = useRef(0)
  const portals = useRef<Group>(null)
  const portalEnd = useRef<Group>(null)
  const materialsRef = useLatest({ material, vortex })
  useFrame((_, delta) => {
    const frame = frameRef.current
    const { material: live, vortex: swirl } = materialsRef.current
    const curve = frame.routeCurves.get(route.id)
    if (!curve) return
    live.uniforms.uA.value.copy(curve.a)
    live.uniforms.uB.value.copy(curve.b)
    live.uniforms.uC.value.copy(curve.c)
    live.uniforms.uResolution.value.set(frame.width / 2, frame.height / 2)
    live.uniforms.uLength.value = curve.a.distanceTo(curve.b)
    live.uniforms.uTime.value = frame.time
    const target = hovered || highlighted ? 1 : 0
    hover.current +=
      (target - hover.current) * Math.min(1, Math.min(delta, 0.1) * HOVER_EASE)
    live.uniforms.uHover.value = hover.current
    if (swirl) swirl.uniforms.uTime.value = frame.time
    if (!portals.current || !portalEnd.current) return
    const length = Math.max(live.uniforms.uLength.value as number, 1e-3)
    const startRadius =
      (layout.worlds.get(route.world_a_id)?.radius ?? 1) *
      (frame.worldScale.get(route.world_a_id) ?? 1)
    const endRadius =
      (layout.worlds.get(route.world_b_id)?.radius ?? 1) *
      (frame.worldScale.get(route.world_b_id) ?? 1)
    const startT = Math.min(0.3, (startRadius * PORTAL_GAP) / length)
    const endT = 1 - Math.min(0.3, (endRadius * PORTAL_GAP) / length)
    bezierAt(curve.a, curve.c, curve.b, startT, point)
    bezierAt(curve.a, curve.c, curve.b, startT + 0.01, ahead)
    portals.current.position.copy(point)
    portals.current.lookAt(ahead)
    portals.current.scale.setScalar(startRadius * PORTAL_SCALE)
    bezierAt(curve.a, curve.c, curve.b, endT, point)
    bezierAt(curve.a, curve.c, curve.b, endT - 0.01, ahead)
    portalEnd.current.position.copy(point)
    portalEnd.current.lookAt(ahead)
    portalEnd.current.scale.setScalar(endRadius * PORTAL_SCALE)
  })
  return (
    <>
      <mesh
        geometry={geometries.ribbon}
        material={material}
        frustumCulled={false}
        renderOrder={1}
      />
      {vortex && ringMaterial && (
        <>
          <group ref={portals}>
            <mesh geometry={geometries.torus} material={ringMaterial} />
            <mesh
              geometry={geometries.plane}
              material={vortex}
              frustumCulled={false}
            />
          </group>
          <group ref={portalEnd}>
            <mesh geometry={geometries.torus} material={ringMaterial} />
            <mesh
              geometry={geometries.plane}
              material={vortex}
              frustumCulled={false}
            />
          </group>
        </>
      )}
    </>
  )
}

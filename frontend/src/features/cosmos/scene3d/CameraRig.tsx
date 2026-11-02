import { type ComponentRef, useEffect, useRef } from 'react'
import { OrbitControls } from '@react-three/drei'
import { useFrame, useThree } from '@react-three/fiber'
import { type PerspectiveCamera, Spherical, Vector3 } from 'three'
import { useScene } from './sceneContext'

export type FocusRequest =
  | { kind: 'world'; id: number; nonce: number }
  | { kind: 'star'; id: number; nonce: number }
  | { kind: 'overview'; nonce: number }

const ELEVATION = 0.92
const FIT_MARGIN = 0.78
const MIN_DISTANCE = 10
const MAX_DISTANCE_FLOOR = 1800
const MAX_DISTANCE_FACTOR = 2.4
const POLAR_MIN = 0.04
const POLAR_MAX = 0.64 * Math.PI
const WORLD_DISTANCE_RADII = 9
const WORLD_DISTANCE_MIN = 34
const MOON_FRAME = 2.4
const STAR_FRAME = 2.2
const FLIGHT_MIN = 1.1
const FLIGHT_MAX = 2.4
const FLIGHT_ZOOM = 0.25
const FLIGHT_TRAVEL = 4000
const AUTO_ROTATE_SPEED = 0.18
const NEAR_SHARE = 0.01
const NEAR_MIN = 0.3
const NEAR_MAX = 30
const NEAR_CHANGE = 0.05

type Flight = {
  fromTarget: Vector3
  toTarget: Vector3
  fromRadius: number
  toRadius: number
  fromTheta: number
  toTheta: number
  fromPhi: number
  toPhi: number
  elapsed: number
  duration: number
}

function easeInOutCubic(t: number): number {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2
}

type CameraRigProps = {
  focus: FocusRequest
  empty: boolean
}

export function CameraRig({ focus, empty }: CameraRigProps) {
  const { layout, frameRef } = useScene()
  const controls = useRef<ComponentRef<typeof OrbitControls>>(null)
  const element = useThree((state) => state.gl.domElement)
  const get = useThree((state) => state.get)
  const flight = useRef<Flight | null>(null)
  const follow = useRef<number | null>(null)
  const interacted = useRef(false)
  const framed = useRef(false)
  const spherical = useRef(new Spherical())
  const offset = useRef(new Vector3())

  const overviewDistance = () => {
    const { size } = get()
    const camera = get().camera as PerspectiveCamera
    const vertical = (camera.fov * Math.PI) / 180
    const horizontal =
      2 *
      Math.atan(
        Math.tan(vertical / 2) * (size.width / Math.max(size.height, 1))
      )
    return (
      (layout.extent / Math.sin(Math.min(vertical, horizontal) / 2)) *
      FIT_MARGIN
    )
  }

  const destination = (
    request: FocusRequest
  ): { target: Vector3; radius: number } | null => {
    if (request.kind === 'overview')
      return {
        target: new Vector3(...layout.center),
        radius: overviewDistance(),
      }
    if (request.kind === 'star') {
      const star = layout.stars.get(request.id)
      if (!star) return null
      return {
        target: new Vector3(...star.position),
        radius: Math.max(star.extent * STAR_FRAME, WORLD_DISTANCE_MIN),
      }
    }
    const body = layout.worlds.get(request.id)
    const position = frameRef.current.worldPosition.get(request.id)
    if (!body || !position) return null
    const scale = frameRef.current.worldScale.get(request.id) ?? 1
    let reach = Math.max(
      body.radius * scale * WORLD_DISTANCE_RADII,
      WORLD_DISTANCE_MIN
    )
    for (const moon of layout.worlds.values())
      if (moon.parentId === request.id)
        reach = Math.max(reach, moon.orbitRadius * MOON_FRAME)
    return { target: position.clone(), radius: reach }
  }

  const fly = (request: FocusRequest, instant: boolean) => {
    const control = controls.current
    const goal = destination(request)
    const camera = get().camera as PerspectiveCamera
    if (!control || !goal) return
    follow.current = request.kind === 'world' ? request.id : null
    offset.current.copy(camera.position).sub(control.target)
    spherical.current.setFromVector3(offset.current)
    const toPhi =
      request.kind === 'overview'
        ? Math.PI / 2 - ELEVATION
        : spherical.current.phi
    if (instant || frameRef.current.reduced) {
      control.target.copy(goal.target)
      spherical.current.set(goal.radius, toPhi, spherical.current.theta)
      camera.position
        .copy(goal.target)
        .add(offset.current.setFromSpherical(spherical.current))
      control.update()
      flight.current = null
      return
    }
    const travel = control.target.distanceTo(goal.target)
    const duration = Math.min(
      FLIGHT_MAX,
      Math.max(
        FLIGHT_MIN,
        FLIGHT_MIN +
          Math.abs(
            Math.log(goal.radius / Math.max(spherical.current.radius, 1e-3))
          ) *
            FLIGHT_ZOOM +
          travel / FLIGHT_TRAVEL
      )
    )
    flight.current = {
      fromTarget: control.target.clone(),
      toTarget: goal.target,
      fromRadius: spherical.current.radius,
      toRadius: goal.radius,
      fromTheta: spherical.current.theta,
      toTheta: spherical.current.theta,
      fromPhi: spherical.current.phi,
      toPhi,
      elapsed: 0,
      duration,
    }
  }

  const flyRef = useRef(fly)
  useEffect(() => {
    flyRef.current = fly
  })

  useEffect(() => {
    if (!framed.current) return
    flyRef.current(focus, false)
  }, [focus])

  useEffect(() => {
    const cancel = (event: PointerEvent) => {
      if (
        event.button !== 0 ||
        event.ctrlKey ||
        event.metaKey ||
        event.shiftKey
      )
        follow.current = null
    }
    const silence = (event: Event) => event.preventDefault()
    element.addEventListener('pointerdown', cancel)
    element.addEventListener('contextmenu', silence)
    return () => {
      element.removeEventListener('pointerdown', cancel)
      element.removeEventListener('contextmenu', silence)
    }
  }, [element])

  useFrame((state, delta) => {
    const frame = frameRef.current
    const camera = state.camera as PerspectiveCamera
    const control = controls.current
    if (!control) return
    if (!framed.current) {
      framed.current = true
      flyRef.current({ kind: 'overview', nonce: 0 }, true)
      if (focus.kind !== 'overview') flyRef.current(focus, true)
    }
    control.maxDistance = Math.max(
      MAX_DISTANCE_FLOOR,
      overviewDistance() * MAX_DISTANCE_FACTOR
    )
    control.autoRotate =
      !empty && !frame.reduced && !interacted.current && flight.current === null
    const active = flight.current
    if (active) {
      active.elapsed += Math.min(delta, 0.1)
      const progress = easeInOutCubic(
        Math.min(1, active.elapsed / active.duration)
      )
      const followed =
        follow.current !== null
          ? frame.worldPosition.get(follow.current)
          : undefined
      if (followed) active.toTarget.copy(followed)
      control.target.lerpVectors(active.fromTarget, active.toTarget, progress)
      const radius = Math.exp(
        Math.log(active.fromRadius) +
          (Math.log(active.toRadius) - Math.log(active.fromRadius)) * progress
      )
      spherical.current.set(
        radius,
        active.fromPhi + (active.toPhi - active.fromPhi) * progress,
        active.fromTheta
      )
      camera.position
        .copy(control.target)
        .add(offset.current.setFromSpherical(spherical.current))
      if (progress >= 1) flight.current = null
    } else if (follow.current !== null) {
      const followed = frame.worldPosition.get(follow.current)
      if (followed) {
        offset.current.copy(followed).sub(control.target)
        control.target.add(offset.current)
        camera.position.add(offset.current)
      }
    }
    const near = Math.min(
      NEAR_MAX,
      Math.max(
        NEAR_MIN,
        camera.position.distanceTo(control.target) * NEAR_SHARE
      )
    )
    if (Math.abs(near - camera.near) / camera.near > NEAR_CHANGE) {
      camera.near = near
      camera.updateProjectionMatrix()
    }
  }, -2)

  return (
    <OrbitControls
      ref={controls}
      makeDefault
      enableDamping
      dampingFactor={0.07}
      rotateSpeed={0.55}
      zoomSpeed={0.9}
      panSpeed={0.8}
      screenSpacePanning={false}
      minDistance={MIN_DISTANCE}
      minPolarAngle={POLAR_MIN}
      maxPolarAngle={POLAR_MAX}
      autoRotateSpeed={AUTO_ROTATE_SPEED}
      onStart={() => {
        interacted.current = true
        flight.current = null
      }}
    />
  )
}

import { useFrame } from '@react-three/fiber'
import { type PerspectiveCamera, Vector3 } from 'three'
import { isUnderway, journeyProgress, routeState } from '../model/cosmosModel'
import { unitHash } from '../model/hash'
import { type Vec3, orbitOffset } from '../model/layout3d'
import { METHOD_LOOK } from '../model/looks'
import {
  type SceneValue,
  type ScreenPoint,
  useScene,
  worldVector,
} from './sceneContext'

const MAX_STEP = 0.1
const MIN_PIXELS = 4.2
const PLANET_LOD_MAX = 3.2
const MOON_LOD_MAX = 2.2
const ROUTE_LIFT = 0.2
const ROUTE_RADIUS_LIFT = 2
const VOYAGE_CYCLE = 26
const VOYAGE_MIN = 0.06
const VOYAGE_MAX = 0.94
const FULL_TURN = Math.PI * 2
const ROUTE_SAMPLES = 48

const scratch = new Vector3()
const starPosition = new Vector3()
const sample = new Vector3()
const offset: Vec3 = [0, 0, 0]
const up = new Vector3(0, 1, 0)
const side = new Vector3()
const span = new Vector3()

export function pixelsPerUnit(
  camera: PerspectiveCamera,
  distance: number,
  height: number
): number {
  const half = Math.tan((camera.fov * Math.PI) / 360)
  return height / 2 / (Math.max(distance, 1e-6) * half)
}

export function project(
  vector: Vector3,
  camera: PerspectiveCamera,
  width: number,
  height: number,
  radius: number,
  out: ScreenPoint
): ScreenPoint {
  scratch.copy(vector).project(camera)
  out.x = ((scratch.x + 1) / 2) * width
  out.y = ((1 - scratch.y) / 2) * height
  out.radius =
    radius * pixelsPerUnit(camera, camera.position.distanceTo(vector), height)
  out.visible = scratch.z > -1 && scratch.z < 1
  return out
}

function screenPoint(map: Map<number, ScreenPoint>, id: number): ScreenPoint {
  let point = map.get(id)
  if (!point) {
    point = { x: 0, y: 0, radius: 0, visible: false }
    map.set(id, point)
  }
  return point
}

export function bezierAt(
  a: Vector3,
  c: Vector3,
  b: Vector3,
  t: number,
  out: Vector3
): Vector3 {
  const u = 1 - t
  return out.set(
    u * u * a.x + 2 * u * t * c.x + t * t * b.x,
    u * u * a.y + 2 * u * t * c.y + t * t * b.y,
    u * u * a.z + 2 * u * t * c.z + t * t * b.z
  )
}

function placeWorlds(scene: SceneValue, camera: PerspectiveCamera) {
  const { layout } = scene
  const frame = scene.frameRef.current
  for (const id of layout.order) {
    const body = layout.worlds.get(id)
    if (!body) continue
    const position = worldVector(frame, id)
    if (body.kind === 'free') {
      position.set(body.anchor[0], body.anchor[1], body.anchor[2])
    } else if (body.kind === 'moon') {
      orbitOffset(body, frame.time, offset)
      const parent = frame.worldPosition.get(body.parentId ?? 0)
      const parentScale = frame.worldScale.get(body.parentId ?? 0) ?? 1
      position.set(
        (parent?.x ?? 0) + offset[0] * parentScale,
        (parent?.y ?? 0) + offset[1] * parentScale,
        (parent?.z ?? 0) + offset[2] * parentScale
      )
    } else {
      orbitOffset(body, frame.time, offset)
      position.set(
        body.anchor[0] + offset[0],
        body.anchor[1] + offset[1],
        body.anchor[2] + offset[2]
      )
    }
    if (body.kind === 'moon') {
      frame.worldScale.set(
        id,
        Math.min(frame.worldScale.get(body.parentId ?? 0) ?? 1, MOON_LOD_MAX)
      )
      continue
    }
    const pixels =
      body.radius *
      pixelsPerUnit(camera, camera.position.distanceTo(position), frame.height)
    frame.worldScale.set(
      id,
      Math.min(Math.max(MIN_PIXELS / Math.max(pixels, 1e-6), 1), PLANET_LOD_MAX)
    )
  }
}

function placeRoutes(scene: SceneValue) {
  const { layout, routeBend, index } = scene
  const frame = scene.frameRef.current
  for (const route of index.data.routes) {
    const a = frame.worldPosition.get(route.world_a_id)
    const b = frame.worldPosition.get(route.world_b_id)
    if (!a || !b) continue
    let curve = frame.routeCurves.get(route.id)
    if (!curve) {
      curve = {
        a: new Vector3(),
        b: new Vector3(),
        c: new Vector3(),
        open: true,
      }
      frame.routeCurves.set(route.id, curve)
    }
    curve.a.copy(a)
    curve.b.copy(b)
    curve.open = routeState(route).open
    span.subVectors(b, a)
    const distance = span.length()
    side.crossVectors(up, span).normalize()
    const radius = layout.worlds.get(route.world_a_id)?.radius ?? 0
    curve.c
      .copy(a)
      .add(b)
      .multiplyScalar(0.5)
      .addScaledVector(
        up,
        distance * ROUTE_LIFT * METHOD_LOOK[route.method].lift +
          radius * ROUTE_RADIUS_LIFT
      )
      .addScaledVector(side, distance * (routeBend.get(route.id) ?? 0))
  }
}

function placeVoyages(scene: SceneValue) {
  const { index } = scene
  const frame = scene.frameRef.current
  for (const journey of index.data.journeys) {
    if (!isUnderway(journey)) continue
    const route = index.route(journey.route_id)
    const curve = route ? frame.routeCurves.get(route.id) : undefined
    if (!route || !curve) continue
    const start = journeyProgress(journey, route)
    const end = Math.min(1, start + 1 / Math.max(route.duration_epochs, 1))
    const cycle = (frame.time / VOYAGE_CYCLE + unitHash(`v${journey.id}`)) % 1
    const phase = frame.reduced ? 0.5 : 0.5 - 0.5 * Math.cos(cycle * FULL_TURN)
    let progress = Math.min(
      VOYAGE_MAX,
      Math.max(VOYAGE_MIN, start + (end - start) * phase)
    )
    if (journey.destination_world_id === route.world_a_id)
      progress = 1 - progress
    let position = frame.voyagePosition.get(journey.id)
    if (!position) {
      position = new Vector3()
      frame.voyagePosition.set(journey.id, position)
    }
    bezierAt(curve.a, curve.c, curve.b, progress, position)
  }
}

function projectAll(scene: SceneValue, camera: PerspectiveCamera) {
  const { layout } = scene
  const frame = scene.frameRef.current
  for (const [id, position] of frame.worldPosition) {
    const body = layout.worlds.get(id)
    if (!body) continue
    project(
      position,
      camera,
      frame.width,
      frame.height,
      body.radius * (frame.worldScale.get(id) ?? 1),
      screenPoint(frame.worldScreen, id)
    )
  }
  for (const star of layout.stars.values()) {
    starPosition.set(star.position[0], star.position[1], star.position[2])
    project(
      starPosition,
      camera,
      frame.width,
      frame.height,
      star.radius,
      screenPoint(frame.starScreen, star.id)
    )
  }
  for (const [id, position] of frame.voyagePosition)
    project(
      position,
      camera,
      frame.width,
      frame.height,
      0,
      screenPoint(frame.voyageScreen, id)
    )
  for (const [id, curve] of frame.routeCurves) {
    let samples = frame.routeScreen.get(id)
    if (!samples) {
      samples = new Float32Array((ROUTE_SAMPLES + 1) * 2)
      frame.routeScreen.set(id, samples)
    }
    for (let step = 0; step <= ROUTE_SAMPLES; step += 1) {
      bezierAt(curve.a, curve.c, curve.b, step / ROUTE_SAMPLES, sample)
      sample.project(camera)
      const behind = sample.z < -1 || sample.z > 1
      samples[step * 2] = behind
        ? Number.NaN
        : ((sample.x + 1) / 2) * frame.width
      samples[step * 2 + 1] = behind
        ? Number.NaN
        : ((1 - sample.y) / 2) * frame.height
    }
  }
}

export function FrameDriver() {
  const scene = useScene()
  const { frameRef } = scene
  useFrame((state, delta) => {
    const frame = frameRef.current
    frame.width = state.size.width
    frame.height = state.size.height
    if (!frame.reduced) frame.time += Math.min(delta, MAX_STEP)
    const camera = state.camera as PerspectiveCamera
    placeWorlds(scene, camera)
    placeRoutes(scene)
    placeVoyages(scene)
  }, -3)
  useFrame((state) => projectAll(scene, state.camera as PerspectiveCamera), 0)
  return null
}

import { type FrameState, type Hover } from './sceneContext'

const WORLD_SLACK = 8
const STAR_REACH = 1.3
const STAR_SLACK = 9
const VOYAGE_REACH = 13
const ROUTE_REACH = 8

function segmentDistance(
  px: number,
  py: number,
  ax: number,
  ay: number,
  bx: number,
  by: number
): number {
  const dx = bx - ax
  const dy = by - ay
  const length = dx * dx + dy * dy
  const t =
    length > 0
      ? Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / length))
      : 0
  return Math.hypot(px - (ax + t * dx), py - (ay + t * dy))
}

export function pick(frame: FrameState, x: number, y: number): Hover {
  let best: { id: number; score: number } | null = null
  for (const [id, point] of frame.worldScreen) {
    if (!point.visible) continue
    const reach = Math.max(point.radius, 2) + WORLD_SLACK
    const distance = Math.hypot(point.x - x, point.y - y)
    if (distance > reach) continue
    const score = distance / reach
    if (!best || score < best.score) best = { id, score }
  }
  if (best) return { kind: 'world', id: best.id }
  for (const [id, point] of frame.starScreen) {
    if (!point.visible) continue
    if (
      Math.hypot(point.x - x, point.y - y) <=
      point.radius * STAR_REACH + STAR_SLACK
    )
      return { kind: 'star', id }
  }
  for (const [id, point] of frame.voyageScreen) {
    if (!point.visible) continue
    if (Math.hypot(point.x - x, point.y - y) <= VOYAGE_REACH)
      return { kind: 'voyage', id }
  }
  let route: { id: number; distance: number } | null = null
  for (const [id, samples] of frame.routeScreen) {
    for (let step = 0; step + 3 < samples.length; step += 2) {
      const ax = samples[step]
      const ay = samples[step + 1]
      const bx = samples[step + 2]
      const by = samples[step + 3]
      if (Number.isNaN(ax) || Number.isNaN(bx)) continue
      const distance = segmentDistance(x, y, ax, ay, bx, by)
      if (distance <= ROUTE_REACH && (!route || distance < route.distance))
        route = { id, distance }
    }
  }
  return route ? { kind: 'route', id: route.id } : null
}

export function sameHover(left: Hover, right: Hover): boolean {
  if (left === null || right === null) return left === right
  return left.kind === right.kind && left.id === right.id
}

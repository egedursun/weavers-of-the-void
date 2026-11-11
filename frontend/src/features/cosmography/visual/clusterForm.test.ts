import { describe, expect, it } from 'vitest'
import {
  CLUSTER_LOOK,
  type ClusterKind,
  type ClusterMember,
  clusterCloud,
  clusterFrame,
  clusterSkeleton,
} from './clusterForm'

const WHITE = () => [1, 1, 1] as [number, number, number]
const COUNT = 3000
const KINDS = Object.keys(CLUSTER_LOOK) as ClusterKind[]

function line(count: number): ClusterMember[] {
  return Array.from({ length: count }, (_, index) => ({
    x: (index - (count - 1) / 2) * 200,
    y: 40,
    z: Math.sin(index) * 20,
    size: 60,
  }))
}

function ring(count: number, radius: number): ClusterMember[] {
  return Array.from({ length: count }, (_, index) => {
    const angle = (index / count) * Math.PI * 2
    return {
      x: Math.cos(angle) * radius,
      y: 40,
      z: Math.sin(angle) * radius,
      size: 50,
    }
  })
}

function pairs(count: number): ClusterMember[] {
  return Array.from({ length: count }, (_, index) => {
    const side = index % 2 === 0 ? -1 : 1
    const order = Math.floor(index / 2)
    return { x: side * (150 + order * 60), y: 40, z: order * 80, size: 50 }
  })
}

function points(kind: ClusterKind, members: ClusterMember[]) {
  const cloud = clusterCloud(kind, members, 900, 7, WHITE, COUNT)
  return {
    cloud,
    list: Array.from({ length: cloud.count }, (_, index) => ({
      x: cloud.positions[index * 3] ?? 0,
      y: cloud.positions[index * 3 + 1] ?? 0,
      z: cloud.positions[index * 3 + 2] ?? 0,
    })),
  }
}

describe('cluster cloud', () => {
  it.each(KINDS)('draws %s as finite light within its budget', (kind) => {
    const { cloud } = points(kind, ring(10, 600))
    expect(cloud.count).toBeGreaterThan(COUNT * 0.6)
    expect(cloud.count).toBeLessThanOrEqual(COUNT)
    for (let index = 0; index < cloud.count * 3; index += 1) {
      expect(Number.isFinite(cloud.positions[index])).toBe(true)
      expect(cloud.colors[index]).toBeGreaterThanOrEqual(0)
    }
  })

  it.each(KINDS)('still draws %s with no galaxy in it', (kind) => {
    expect(points(kind, []).cloud.count).toBeGreaterThan(0)
  })

  it('keeps the heart of a void dark', () => {
    const { cloud, list } = points('void', ring(10, 600))
    const [cx, , cz] = cloud.centre
    const inside = list.filter(
      (point) => Math.hypot(point.x - cx, point.z - cz) < cloud.ring * 0.45
    ).length
    expect(inside / list.length).toBeLessThan(0.08)
  })

  it('lays a filament along its galaxies', () => {
    const members = line(9)
    const { cloud, list } = points('filament', members)
    const across = list.map((point) =>
      Math.abs(
        -(point.x - cloud.centre[0]) * Math.sin(cloud.angle) +
          (point.z - cloud.centre[2]) * Math.cos(cloud.angle)
      )
    )
    const near = across.filter((value) => value < cloud.major * 0.25).length
    expect(near / across.length).toBeGreaterThan(0.85)
  })

  it('reflects a mirror cluster across its seam', () => {
    const { cloud, list } = points('mirror_cluster', pairs(10))
    const [cx] = cloud.centre
    const left = list.filter((point) => point.x < cx - 1).length
    const right = list.filter((point) => point.x > cx + 1).length
    expect(Math.abs(left - right) / list.length).toBeLessThan(0.02)
  })

  it('aligns the frame with the long side of its galaxies', () => {
    const frame = clusterFrame(line(7), 900)
    expect(Math.abs(Math.cos(frame.angle))).toBeGreaterThan(0.95)
    expect(frame.major).toBeGreaterThan(frame.minor * 2.5)
  })

  it.each(KINDS)('lights the outline of %s with its own lines', (kind) => {
    const members = ring(10, 600)
    const lines = clusterSkeleton(kind, members, clusterFrame(members, 900))
    expect(lines.length).toBeGreaterThanOrEqual(2)
    expect(lines.length % 2).toBe(0)
  })

  it('threads a filament through its galaxies in one chain', () => {
    const members = line(9)
    const lines = clusterSkeleton(
      'filament',
      members,
      clusterFrame(members, 900)
    )
    expect(lines.length / 2).toBe(members.length - 1)
  })

  it('closes the rim of a void into one ring', () => {
    const members = ring(10, 600)
    const lines = clusterSkeleton('void', members, clusterFrame(members, 900))
    expect(lines.length / 2).toBe(members.length)
  })
})

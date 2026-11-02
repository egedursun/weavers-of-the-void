import {
  BufferAttribute,
  BufferGeometry,
  ConeGeometry,
  CylinderGeometry,
  DodecahedronGeometry,
  IcosahedronGeometry,
  PlaneGeometry,
  RingGeometry,
  SphereGeometry,
  TetrahedronGeometry,
  TorusGeometry,
} from 'three'
import { type QualityPreset } from './quality'

const RIBBON_SEGMENTS = 120
const ORBIT_SEGMENTS = 256
const RING_SEGMENTS = 192
const BEAM_SEGMENTS = 24
const TORUS_RADIAL = 12
const TORUS_TUBULAR = 64

export type SharedGeometries = {
  sphere: BufferGeometry
  crystal: BufferGeometry
  rock: BufferGeometry
  ship: BufferGeometry
  plane: BufferGeometry
  ribbon: BufferGeometry
  orbit: BufferGeometry
  ring: BufferGeometry
  disk: BufferGeometry
  beam: BufferGeometry
  shard: BufferGeometry
  torus: BufferGeometry
}

export function ribbonGeometry(segments = RIBBON_SEGMENTS): BufferGeometry {
  const positions = new Float32Array((segments + 1) * 2 * 3)
  const along = new Float32Array((segments + 1) * 2)
  const sides = new Float32Array((segments + 1) * 2)
  const indices: number[] = []
  for (let step = 0; step <= segments; step += 1) {
    const t = step / segments
    for (let edge = 0; edge < 2; edge += 1) {
      const vertex = step * 2 + edge
      along[vertex] = t
      sides[vertex] = edge === 0 ? -1 : 1
    }
    if (step < segments) {
      const base = step * 2
      indices.push(base, base + 1, base + 2, base + 1, base + 3, base + 2)
    }
  }
  const geometry = new BufferGeometry()
  geometry.setAttribute('position', new BufferAttribute(positions, 3))
  geometry.setAttribute('aT', new BufferAttribute(along, 1))
  geometry.setAttribute('aSide', new BufferAttribute(sides, 1))
  geometry.setIndex(indices)
  geometry.boundingSphere = null
  return geometry
}

export function orbitGeometry(segments = ORBIT_SEGMENTS): BufferGeometry {
  const positions = new Float32Array((segments + 1) * 3)
  const angles = new Float32Array(segments + 1)
  for (let step = 0; step <= segments; step += 1) {
    const angle = (step / segments) * Math.PI * 2
    positions[step * 3] = Math.cos(angle)
    positions[step * 3 + 1] = 0
    positions[step * 3 + 2] = Math.sin(angle)
    angles[step] = step / segments
  }
  const geometry = new BufferGeometry()
  geometry.setAttribute('position', new BufferAttribute(positions, 3))
  geometry.setAttribute('aAngle', new BufferAttribute(angles, 1))
  return geometry
}

export function createGeometries(preset: QualityPreset): SharedGeometries {
  const beam = new ConeGeometry(1, 1, BEAM_SEGMENTS, 1, true)
  beam.translate(0, -0.5, 0)
  const ship = new CylinderGeometry(0.45, 0.45, 2.2, 24, 1)
  ship.rotateZ(Math.PI / 2)
  return {
    sphere: new SphereGeometry(1, preset.widthSegments, preset.heightSegments),
    crystal: new IcosahedronGeometry(1, 2),
    rock: new DodecahedronGeometry(1, 0),
    ship,
    plane: new PlaneGeometry(2, 2),
    ribbon: ribbonGeometry(),
    orbit: orbitGeometry(),
    ring: new RingGeometry(1.32, 2.25, RING_SEGMENTS, 1),
    disk: new RingGeometry(1.35, 3.9, RING_SEGMENTS, 1),
    beam,
    shard: new TetrahedronGeometry(1, 0),
    torus: new TorusGeometry(1, 0.06, TORUS_RADIAL, TORUS_TUBULAR),
  }
}

export function disposeGeometries(geometries: SharedGeometries): void {
  for (const geometry of Object.values(geometries)) geometry.dispose()
}

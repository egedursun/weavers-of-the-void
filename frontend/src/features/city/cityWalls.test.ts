import { describe, expect, it } from 'vitest'
import { gateCount, roadTiles, wallPieces } from './cityWalls'
import { type Cell, hexDistance, hexRing, hexToWorld } from './hex'

const HALF_TURN = 180

function degrees(radians: number): number {
  return (radians * HALF_TURN) / Math.PI
}

function wrap(value: number): number {
  return ((((value + HALF_TURN) % 360) + 360) % 360) - HALF_TURN
}

function angleTo(from: Cell, to: Cell): number {
  const [fx, fz] = hexToWorld(from[0], from[1])
  const [tx, tz] = hexToWorld(to[0], to[1])
  return degrees(Math.atan2(tz - fz, tx - fx))
}

function edgesOf(model: string, turn: number): number[] {
  const local =
    model === 'corner_wide'
      ? [HALF_TURN, -60]
      : model === 'corner_sharp'
        ? [HALF_TURN, -120]
        : [0, HALF_TURN]
  return local.map((angle) => wrap(angle - degrees(turn)))
}

describe('city walls', () => {
  it('runs stone walls through every ring hex so each piece meets its neighbours', () => {
    const radius = 4
    const ring = hexRing(radius)
    const pieces = wallPieces(radius, 3, 2)
    expect(pieces).toHaveLength(ring.length)
    expect(
      pieces.filter((piece) => piece.model === 'corner_wide')
    ).toHaveLength(6)
    expect(pieces.filter((piece) => piece.model === 'gate')).toHaveLength(
      gateCount(2)
    )
    pieces.forEach((piece, index) => {
      if (piece.model === 'tower') return
      const back = angleTo(
        piece.cell,
        ring[(index + ring.length - 1) % ring.length]
      )
      const ahead = angleTo(piece.cell, ring[(index + 1) % ring.length])
      const edges = edgesOf(piece.model, piece.turn).sort((a, b) => a - b)
      const wanted = [wrap(back), wrap(ahead)].sort((a, b) => a - b)
      edges.forEach((edge, at) =>
        expect(Math.abs(wrap(edge - wanted[at]))).toBeLessThan(1)
      )
    })
  })

  it('crowns the corners with towers once the walls are strong enough', () => {
    expect(
      wallPieces(3, 4, 0).filter((piece) => piece.model === 'tower')
    ).toHaveLength(6)
    expect(
      wallPieces(3, 3, 0).filter((piece) => piece.model === 'tower')
    ).toHaveLength(0)
  })

  it('rings a weakly walled town with fences on the hex edges facing its inside', () => {
    const pieces = wallPieces(3, 1, 0)
    expect(
      pieces.every(
        (piece) => piece.model === 'fence' || piece.model === 'fence_gate'
      )
    ).toBe(true)
    pieces.forEach((piece) => {
      const edge = wrap(HALF_TURN - degrees(piece.turn))
      const inner = hexRing(1)
        .map(
          (step) => [piece.cell[0] + step[0], piece.cell[1] + step[1]] as Cell
        )
        .find((near) => Math.abs(wrap(angleTo(piece.cell, near) - edge)) < 1)
      expect(inner && hexDistance(inner, [0, 0])).toBe(2)
    })
    expect(pieces.filter((piece) => piece.model === 'fence_gate')).toHaveLength(
      1
    )
  })

  it('lays road tiles that meet the hexes before and after them along the way out', () => {
    const tiles = roadTiles(3, 1, 3)
    expect(tiles.filter((tile) => tile.model === 'end')).toHaveLength(
      gateCount(1)
    )
    const local: Record<string, number[]> = {
      straight: [0, HALF_TURN],
      bend: [HALF_TURN, -60],
      sharp: [HALF_TURN, -120],
      end: [HALF_TURN],
    }
    for (const tile of tiles) {
      const edges = local[tile.model].map((angle) =>
        wrap(angle - degrees(tile.turn))
      )
      const neighbours = hexRing(1)
        .map((step) => [tile.cell[0] + step[0], tile.cell[1] + step[1]] as Cell)
        .filter(
          (near) =>
            tiles.some(
              (other) => other.cell[0] === near[0] && other.cell[1] === near[1]
            ) || hexDistance(near, [0, 0]) === 2
        )
        .map((near) => wrap(angleTo(tile.cell, near)))
      edges.forEach((edge) =>
        expect(
          neighbours.some((angle) => Math.abs(wrap(angle - edge)) < 1)
        ).toBe(true)
      )
    }
  })

  it('draws no walls without walls and more roads out of more gates', () => {
    expect(wallPieces(3, 0, 2)).toEqual([])
    expect(roadTiles(3, 0, 3)).toEqual([])
    expect(roadTiles(3, 1, 3)).toHaveLength(gateCount(1) * 4)
    expect(roadTiles(3, 3, 3)).toHaveLength(gateCount(3) * 4)
    expect(gateCount(9)).toBe(6)
  })
})

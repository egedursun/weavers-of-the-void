import { describe, expect, it } from 'vitest'
import { overlaps, placeLabels, verticalShifts } from './labelLayout'

describe('label placement', () => {
  it('never places two labels on top of each other', () => {
    const candidates = Array.from({ length: 30 }, (_, index) => ({
      id: String(index),
      x: 100 + (index % 3) * 4,
      y: 100,
      width: 80,
      height: 14,
      priority: index,
    }))
    const placed = placeLabels(candidates)
    for (let first = 0; first < placed.length; first += 1)
      for (let second = first + 1; second < placed.length; second += 1)
        expect(overlaps(placed[first].box, placed[second].box)).toBe(false)
    expect(placed[0].id).toBe('29')
  })

  it('shifts a label vertically before hiding it', () => {
    const placed = placeLabels(
      [
        { id: 'big', x: 50, y: 50, width: 60, height: 12, priority: 10 },
        {
          id: 'small',
          x: 50,
          y: 50,
          width: 60,
          height: 12,
          priority: 1,
          shifts: verticalShifts(12, 2),
        },
      ],
      { padding: 0 }
    )
    expect(placed.map((label) => label.id)).toEqual(['big', 'small'])
    expect(placed[1].y).not.toBe(50)
  })

  it('keeps important labels and respects obstacles and bounds', () => {
    const obstacle = { left: 0, top: 0, right: 100, bottom: 100 }
    const placed = placeLabels(
      [
        { id: 'hidden', x: 50, y: 50, width: 20, height: 10, priority: 5 },
        {
          id: 'kept',
          x: 50,
          y: 50,
          width: 20,
          height: 10,
          priority: 1,
          always: true,
        },
        { id: 'outside', x: 500, y: 50, width: 20, height: 10, priority: 1 },
      ],
      {
        obstacles: [obstacle],
        bounds: { left: 0, top: 0, right: 300, bottom: 300 },
      }
    )
    expect(placed.map((label) => label.id)).toEqual(['kept'])
  })
})

import { describe, expect, it } from 'vitest'
import { type MapView, type WorldMap } from './api'
import {
  MAX_ZOOM,
  MIN_ZOOM,
  fitTransform,
  leagues,
  markerRadius,
  populationTrend,
  tierOf,
  toMap,
  toScreen,
  zoomAt,
} from './mapModel'
import { validateMapSearch } from './mapRouteSearch'

const MAP = {
  extent: {
    x: 100,
    y: 200,
    width: 400,
    height: 200,
    known_ratio: 1,
    known_cells: 10,
  },
} as unknown as WorldMap

describe('map viewport', () => {
  it('fits the known area into the frame and round-trips coordinates', () => {
    const fit = fitTransform(MAP, { width: 800, height: 400 })
    const centre = toScreen(fit, 300, 300)
    expect(centre.x).toBeCloseTo(400)
    expect(centre.y).toBeCloseTo(200)
    const back = toMap(fit, centre.x, centre.y)
    expect(back.x).toBeCloseTo(300)
  })

  it('clamps zoom to the allowed range around the fit', () => {
    const fit = fitTransform(MAP, { width: 800, height: 400 })
    const far = zoomAt(fit, fit, 1000, 0, 0)
    expect(far.k).toBeCloseTo(fit.k * MAX_ZOOM)
    const near = zoomAt(fit, fit, 0.0001, 0, 0)
    expect(near.k).toBeCloseTo(fit.k * MIN_ZOOM)
  })

  it('formats leagues and marker sizes', () => {
    expect(leagues(55)).toBe('5.5')
    expect(leagues(250)).toBe('25')
    expect(markerRadius('people', 9)).toBe(9.5)
    expect(markerRadius('mortal', 10)).toBeCloseTo(10.5)
  })
})

describe('settlements', () => {
  it('detects population trends above the rule threshold only', () => {
    expect(populationTrend(1100, 1000, 5)).toBe('up')
    expect(populationTrend(1020, 1000, 5)).toBeNull()
    expect(populationTrend(800, 1000, 5)).toBe('down')
    expect(populationTrend(800, null, 5)).toBeNull()
  })

  it('prefers the server tier and falls back to population thresholds', () => {
    const view = {
      settlements: {
        '1': { tier: 'capital', population: 10, previous_population: null },
      },
      population: { '2': 12000, '3': 10, '4': 2000000, '5': 20000000 },
    } as unknown as MapView
    const thresholds = {
      town: 2000,
      city: 10000,
      greatCity: 50000,
      megacity: 1000000,
      conurbation: 10000000,
    }
    expect(tierOf(view, 1, thresholds)).toBe('capital')
    expect(tierOf(view, 2, thresholds)).toBe('city')
    expect(tierOf(view, 3, thresholds)).toBe('village')
    expect(tierOf(view, 4, thresholds)).toBe('megacity')
    expect(tierOf(view, 5, thresholds)).toBe('conurbation')
  })
})

describe('map search parameters', () => {
  it('keeps only positive integer parameters', () => {
    expect(validateMapSearch({ world: '3', epoch: 'x', focus: -1 })).toEqual({
      world: 3,
    })
  })
})

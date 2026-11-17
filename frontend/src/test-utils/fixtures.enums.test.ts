import { describe, expect, it } from 'vitest'
import {
  atmosphereValues,
  climateEraValues,
  discoveryValues,
  domainValues,
  entityTypeValues,
  gravityValues,
  starTypeValues,
  travelMethodValues,
  worldTypeValues,
} from '@/api/generated/schema'
import cosmos from '../../e2e/fixtures/cosmos.json'
import mapGraph from '../../e2e/fixtures/mapGraph.json'

const LABELLED = new Set(['guide'])

const FIELDS: Record<string, ReadonlyArray<string>> = {
  method: travelMethodValues,
  star_type: starTypeValues,
  world_type: worldTypeValues,
  discovery: discoveryValues,
  gravity: gravityValues,
  atmosphere: atmosphereValues,
  entity_type: entityTypeValues,
  domain_primary: domainValues,
  domain_secondary: domainValues,
  climate_era: climateEraValues,
}

function staleValues(node: unknown, path: string, found: string[]) {
  if (Array.isArray(node)) {
    node.forEach((item, index) => staleValues(item, `${path}[${index}]`, found))
    return
  }
  if (node === null || typeof node !== 'object') return
  for (const [key, value] of Object.entries(node)) {
    const allowed = FIELDS[key]
    if (allowed && typeof value === 'string' && !allowed.includes(value))
      found.push(`${path}.${key}=${value}`)
    if (!LABELLED.has(key)) staleValues(value, `${path}.${key}`, found)
  }
}

describe('recorded fixtures', () => {
  it('hold only enum values the API still serves', () => {
    const found: string[] = []
    staleValues(cosmos, 'cosmos', found)
    staleValues(mapGraph, 'mapGraph', found)
    expect(found).toEqual([])
  })
})

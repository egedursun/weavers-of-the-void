import { describe, expect, it } from 'vitest'
import { HOUSING, RACKETS, SERVICES, STANCES } from './labels'

describe('the deepened town values', () => {
  it('labels shacks and palaces, lighting and pest control, new rackets and integration', () => {
    expect(HOUSING.shack.label).toBe('Shacks')
    expect(HOUSING.palace.label).toBe('Palaces')
    expect(SERVICES.lighting.label).toBe('Street lighting')
    expect(SERVICES.pest_control.label).toBe('Pest control')
    expect(RACKETS.forgery.label).toBe('Forged papers')
    expect(STANCES.integrate.label).toBe('Integrated')
  })
})

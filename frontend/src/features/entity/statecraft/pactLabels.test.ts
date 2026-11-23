import { describe, expect, it } from 'vitest'
import {
  crisisStateValues,
  partyRoleValues,
  regionalStandingValues,
  treatyStatusValues,
} from '@/api/generated/schema'
import { PARTY_ROLES, TREATY_STATUSES } from '@/features/entity/realm/labels'
import { CRISIS_STATES, STANDINGS } from './labels'

describe('pact labels', () => {
  it('names every party role, treaty state, crisis state and standing', () => {
    for (const role of partyRoleValues)
      expect(PARTY_ROLES[role].label).toBeTruthy()
    for (const state of treatyStatusValues)
      expect(TREATY_STATUSES[state].label).toBeTruthy()
    for (const state of crisisStateValues)
      expect(CRISIS_STATES[state].label).toBeTruthy()
    for (const standing of regionalStandingValues)
      expect(STANDINGS[standing].label).toBeTruthy()
    expect(PARTY_ROLES.mediator.label).toBe('Mediator')
    expect(TREATY_STATUSES.suspended.label).toBe('Suspended')
    expect(CRISIS_STATES.mediated.label).toBe('Settled by a mediator')
    expect(STANDINGS.neutral.label).toBe('Neutral')
  })
})

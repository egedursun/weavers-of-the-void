import { describe, expect, it } from 'vitest'
import {
  airNeedValues,
  bargainGainValues,
  bargainPriceValues,
  gravityValues,
  impactBodyValues,
  impactOutcomeValues,
  lawExceptionValues,
  lifeEnvironmentValues,
  worldEndCauseValues,
  worldEndValues,
} from '@/api/generated/schema'
import { GRAVITY_LABEL } from '@/features/cosmos/model/labels'
import { GAINS, LAW_EXCEPTIONS, PRICES } from '@/features/divine/labels'
import { WORLD_END_CAUSES, WORLD_ENDS } from '@/features/lifecycle/labels'
import {
  AIR_NEEDS,
  ENVIRONMENTS,
  IMPACT_BODIES,
  IMPACT_OUTCOMES,
} from './labels'

function labelsEvery(
  values: ReadonlyArray<string>,
  labels: Record<string, unknown>
) {
  expect(Object.keys(labels).sort()).toEqual([...values].sort())
}

describe('laws, bargains, heavens, falls and ends of worlds', () => {
  it('labels every new value the heavens and the ends of worlds serve', () => {
    labelsEvery(gravityValues, GRAVITY_LABEL)
    labelsEvery(airNeedValues, AIR_NEEDS)
    labelsEvery(lifeEnvironmentValues, ENVIRONMENTS)
    labelsEvery(impactBodyValues, IMPACT_BODIES)
    labelsEvery(impactOutcomeValues, IMPACT_OUTCOMES)
    labelsEvery(worldEndValues, WORLD_ENDS)
    labelsEvery(worldEndCauseValues, WORLD_END_CAUSES)
  })

  it('labels every exception of a law and every gain and price of a bargain', () => {
    labelsEvery(lawExceptionValues, LAW_EXCEPTIONS)
    labelsEvery(bargainGainValues, GAINS)
    labelsEvery(bargainPriceValues, PRICES)
    expect(LAW_EXCEPTIONS.named_kind).toBeTruthy()
    expect(IMPACT_BODIES.wreck.label).toBeTruthy()
    expect(WORLD_ENDS.devoured.label).toBeTruthy()
  })
})

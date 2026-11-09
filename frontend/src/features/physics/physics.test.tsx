import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { LifeClassSection } from './LifeClassSection'
import { WorldSurveySection } from './SurveySection'
import {
  WorldImpactsSection,
  WorldTerraformSection,
} from './WorldShapingSection'
import { WORLD_PHYSICS } from './physicsFixtures'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

function serveWorld() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 12 },
  })
  onApi('GET', '/api/names', [])
  onApi('GET', '/api/physics/worlds/11', WORLD_PHYSICS)
}

describe('the physics of a world', () => {
  beforeEach(resetApi)

  it('turns a foreseen body aside', async () => {
    serveWorld()
    onApi('POST', '/api/actions/impact:deflect', ACCEPTED_ACTION)
    const { screen } = await renderApp(<WorldImpactsSection worldId={11} />)
    await expect
      .element(screen.getByText(/strikes in 2 epochs, foreseen/))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Turn aside' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/impact:deflect'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/impact:deflect')[0].body).toEqual({
      impact_id: 81,
    })
  })

  it('sends the places life dwells in as a list', async () => {
    serveWorld()
    onApi('POST', '/api/actions/life_class:edit', ACCEPTED_ACTION)
    const { screen } = await renderApp(<LifeClassSection worldId={11} />)
    await screen.getByRole('button', { name: 'Land' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/life_class:edit'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/life_class:edit')[0].body).toEqual({
      world_id: 11,
      values: { environments: ['marine', 'terrestrial'] },
      release: [],
    })
  })

  it('stops a work of reshaping', async () => {
    serveWorld()
    onApi('POST', '/api/actions/terraform:stop', ACCEPTED_ACTION)
    const { screen } = await renderApp(<WorldTerraformSection worldId={11} />)
    await expect.element(screen.getByText(/3 epochs left/)).toBeVisible()
    await screen.getByRole('button', { name: 'Stop' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/terraform:stop'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/terraform:stop')[0].body).toEqual({
      project_id: 71,
    })
  })

  it('makes a people forget the world', async () => {
    serveWorld()
    onApi('POST', '/api/actions/survey:forget', ACCEPTED_ACTION)
    const { screen } = await renderApp(<WorldSurveySection worldId={11} />)
    await expect
      .element(screen.getByText(/Observed since epoch 11/))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Make them forget it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/survey:forget'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/survey:forget')[0].body).toEqual({
      survey_id: 91,
    })
  })
})

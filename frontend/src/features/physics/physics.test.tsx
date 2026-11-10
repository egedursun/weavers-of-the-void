import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { LifeClassSection } from './LifeClassSection'
import { StarEvolutionSection } from './StarEvolutionSection'
import { WorldSurveySection } from './SurveySection'
import { WorldPhysicsSection } from './WorldPhysicsSection'
import {
  WorldImpactsSection,
  WorldTerraformSection,
} from './WorldShapingSection'
import { STAR_PHYSICS, WORLD_PHYSICS } from './physicsFixtures'

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

  it('shows the calendar of its sky and holds a value the heavens derive', async () => {
    serveWorld()
    onApi('POST', '/api/actions/world_physics:edit', ACCEPTED_ACTION)
    const { screen } = await renderApp(<WorldPhysicsSection worldId={11} />)
    await expect.element(screen.getByText('Epoch 15')).toBeVisible()
    await expect.element(screen.getByText('Sennet at epoch 20')).toBeVisible()
    await screen.getByRole('button', { name: 'Adjust' }).nth(4).click()
    await screen.getByRole('combobox', { name: 'Ringed' }).click()
    await screen.getByRole('option', { name: 'Yes' }).click()
    await screen
      .getByRole('button', { name: 'Hold these values' })
      .first()
      .click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/world_physics:edit'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/world_physics:edit')[0].body).toEqual({
      world_id: 11,
      values: { ringed: true },
      release: [],
    })
  })

  it('sends the maker it picks as an id', async () => {
    serveWorld()
    onApi('GET', '/api/physics/stars/246', STAR_PHYSICS)
    onApi('GET', '/api/sons', [{ son: { id: 7, name: 'Veyr' } }])
    onApi('POST', '/api/actions/star_physics:edit', ACCEPTED_ACTION)
    const { screen } = await renderApp(<StarEvolutionSection starId={246} />)
    await screen.getByRole('button', { name: 'Adjust' }).first().click()
    await screen.getByRole('combobox', { name: 'Maker who keeps it' }).click()
    await screen.getByRole('option', { name: 'Veyr' }).click()
    await screen
      .getByRole('button', { name: 'Hold these values' })
      .first()
      .click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/star_physics:edit'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/star_physics:edit')[0].body).toEqual({
      star_id: 246,
      values: { maker_son_id: 7 },
      release: [],
    })
  })
})

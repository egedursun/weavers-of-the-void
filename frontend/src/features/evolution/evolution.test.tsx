import {
  ACCEPTED_ACTION,
  callsTo,
  failure,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { EvolutionSection } from './EvolutionSection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const DEER = { id: 30, kind: 'entity' as const, name: 'Reed Deer' }
const VALE = { id: 40, kind: 'entity' as const, name: 'Low Vale' }
const COUGH = { id: 50, kind: 'entity' as const, name: 'Grey Cough' }
const ORA = { id: 41, kind: 'entity' as const, name: 'Ora' }

const EMPTY = {
  history: [],
  species: null,
  traits: [],
  marks: [],
  services: [],
  trophic: [],
  land: null,
  herds: [],
  pathogen: null,
  carriers: [],
  responses: [],
  research: [],
  cycles: [],
}

function serveBase() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 6 },
  })
  onApi('GET', '/api/names', [
    { kind: 'entity', id: 30, name: 'Reed Deer', type: 'species', world_id: 1 },
    { kind: 'entity', id: 40, name: 'Low Vale', type: 'region', world_id: 1 },
    {
      kind: 'entity',
      id: 50,
      name: 'Grey Cough',
      type: 'disease',
      world_id: 1,
    },
  ])
}

describe('evolution', () => {
  beforeEach(() => resetApi())

  it('shows a species’ stocks, line and role and draws a trait anew', async () => {
    serveBase()
    onApi('GET', '/api/evolution/of/30', {
      ...EMPTY,
      node: DEER,
      history: [
        { trait: 'wariness', epoch: 4, value: 60 },
        { trait: 'wariness', epoch: 5, value: 72 },
      ],
      species: {
        keystone: 'pollinator',
        feral_epoch: 4,
        trophic_level: 'herbivore',
        stage: 'wild',
        locked: [],
      },
      traits: [
        {
          species: DEER,
          region: VALE,
          trait: 'wariness',
          mean: 72,
          variance: 12,
          updated_epoch: 5,
          locked: [],
        },
      ],
      marks: [
        {
          package: 'divine_blessing',
          blessing: true,
          source: null,
          epoch: 3,
          locked: [],
        },
      ],
      services: [
        {
          region: VALE,
          role: 'pollinator',
          species: DEER,
          strength: 64,
          epoch: 5,
          locked: [],
        },
      ],
      herds: [
        {
          community: ORA,
          species: DEER,
          head: 30,
          stage: 'herded',
        },
      ],
    })
    onApi('POST', '/api/actions/species_trait:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<EvolutionSection nodeId={30} />)
    await expect
      .element(screen.getByText('Pollinator of its lands'))
      .toBeVisible()
    await expect.element(screen.getByText('Wariness')).toBeVisible()
    await expect.element(screen.getByText('in epoch 4')).toBeVisible()
    await expect
      .element(screen.getByRole('img', { name: 'Traits over the epochs' }))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Draw anew' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/species_trait:delete'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/species_trait:delete')[0].body
    ).toEqual({
      species_id: 30,
      region_id: 40,
      trait: 'wariness',
    })
  })

  it('shows a sickness’ carriers, answers and cures and frees a carrier', async () => {
    serveBase()
    onApi('GET', '/api/evolution/of/50', {
      ...EMPTY,
      node: COUGH,
      pathogen: {
        cold_tolerance: 60,
        heat_tolerance: 40,
        resistance: 20,
        locked: [],
      },
      carriers: [
        {
          mortal: ORA,
          disease: COUGH,
          home_region: VALE,
          identified: false,
          seeded: 2,
          since_epoch: 3,
          locked: [],
        },
      ],
      responses: [
        {
          community: ORA,
          disease: COUGH,
          response: 'quarantine',
          strength: 60,
          since_epoch: 4,
          until_epoch: 6,
          locked: [],
        },
      ],
      research: [
        {
          institution: VALE,
          disease: COUGH,
          points: 40,
          threshold: 100,
          specimens: 3,
          started_epoch: 2,
          cured_epoch: null,
          locked: [],
        },
      ],
    })
    onApi('POST', '/api/actions/carrier:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<EvolutionSection nodeId={50} />)
    await expect.element(screen.getByText('2 outbreaks seeded')).toBeVisible()
    await expect
      .element(
        screen.getByText('since epoch 4, until epoch 6', { exact: false })
      )
      .toBeVisible()
    await expect.element(screen.getByText('3 specimens studied')).toBeVisible()
    await screen.getByRole('button', { name: 'Free' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/carrier:delete'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/carrier:delete')[0].body).toEqual({
      mortal_id: 41,
      disease_id: 50,
    })
  })

  it('says why the living world could not be read', async () => {
    serveBase()
    onApi(
      'GET',
      '/api/evolution/of/30',
      failure(500, 'The heavens are silent.')
    )
    const { screen } = await renderApp(<EvolutionSection nodeId={30} />)
    await expect
      .element(screen.getByText('The living world could not be read'))
      .toBeVisible()
  })
})

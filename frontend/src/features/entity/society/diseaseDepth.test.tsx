import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { DemographySection } from './Demography'
import { DiseaseSection } from './DiseaseCard'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const OUTBREAK = {
  id: 3,
  disease_id: 41,
  disease: 'the marsh ague',
  region_id: 7,
  region: 'Vale',
  source_region_id: null,
  path: 'origin',
  status: 'active',
  severity: 64,
  infected: 4200,
  dead: 610,
  started_epoch: 50,
  ended_epoch: null,
  quarantined: false,
  event_id: null,
  locked: ['severity'],
  unseen_pct: 36,
}

const DISEASE = {
  entity_id: 41,
  name: 'the marsh ague',
  primary_route: 'bite',
  primary_share: 80,
  routes: [{ route: 'blood', share: 20, held: false }],
  virulence: 52,
  lethality: 33,
  chronic_rate: 22,
  incubation: 3,
  target_functions: ['breath', 'cognition'],
  affinity_warmth: 'any',
  affinity_moisture: 'wet',
  host_species_id: 90,
  immunity_epochs: 8,
  mutation_rate: 5,
  stigma: 20,
  cure_level: 4,
  generation: 0,
  parent_id: null,
  origin_region_id: 7,
  emerged_epoch: 50,
  locked: ['target_functions'],
  strains: [],
  outbreaks: [OUTBREAK],
  endemic: [
    {
      region_id: 7,
      region: 'Vale',
      load: 30,
      since_epoch: 48,
      locked: true,
      disease_id: 41,
      disease: 'the marsh ague',
    },
  ],
  cures: [],
  immunities: [],
  origin_incident_id: 12,
  origin: {
    id: 12,
    epoch: 50,
    year: 7,
    kind: 'disease.emerged',
    text: 'A new sickness rose in Vale: the marsh ague, borne by bite.',
    place_id: 7,
  },
  incidents: [
    {
      id: 12,
      epoch: 50,
      year: 7,
      kind: 'disease.emerged',
      text: 'A new sickness rose in Vale: the marsh ague, borne by bite.',
      place_id: 7,
    },
  ],
  hosts: [
    {
      species_id: 90,
      name: 'Marsh Rats',
      immune: false,
      lands: 3,
      abundance: 70,
      primary: true,
    },
  ],
  unseen_pct: 36,
  sick: 840,
}

const DEMOGRAPHY = {
  entity_id: 30,
  people_id: null,
  sex_kinds: ['bearer', 'begetter'],
  cohorts: [
    {
      age_band: 'adult',
      sex_kind: 'begetter',
      social_class: 'farmer',
      condition: 'none',
      count: 1200,
    },
    {
      age_band: 'adult',
      sex_kind: 'begetter',
      social_class: 'farmer',
      condition: 'sick',
      count: 300,
    },
    {
      age_band: 'adult',
      sex_kind: 'bearer',
      social_class: 'farmer',
      condition: 'maimed',
      count: 40,
    },
  ],
  labour: [],
  flows: [],
  pressures: [],
  classes: [],
  biology: null,
  culture: null,
  values: [],
  neighbours: [],
  inequality: 10,
  mobilisation_pct: 90,
  afflictions: [
    {
      disease_id: 41,
      disease: 'the marsh ague',
      primary_route: 'bite',
      target_functions: ['breath'],
      severity: 64,
      status: 'active',
      outbreak_id: 3,
    },
  ],
  named: [
    { id: 501, name: 'Oswin', dormant: true, held: false, importance: 4 },
    { id: 502, name: 'Hild', dormant: false, held: true, importance: 30 },
  ],
  held: ['sick'],
}

function serve() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 50 },
  })
  onApi('GET', '/api/names', [
    { id: 7, kind: 'entity', type: 'region', name: 'Vale', world_id: 1 },
    {
      id: 41,
      kind: 'entity',
      type: 'disease',
      name: 'the marsh ague',
      world_id: 1,
    },
    {
      id: 90,
      kind: 'entity',
      type: 'species',
      name: 'Marsh Rats',
      world_id: 1,
    },
    {
      id: 30,
      kind: 'entity',
      type: 'settlement',
      name: 'Fenwick',
      world_id: 1,
    },
  ])
}

describe('disease depth and cohorts', () => {
  beforeEach(resetApi)

  it('forges a new sickness from the designer', async () => {
    serve()
    onApi('GET', '/api/entities/41/disease', DISEASE)
    onApi('POST', '/api/actions/disease:create', ACCEPTED_ACTION)
    const { screen } = await renderApp(<DiseaseSection diseaseId={41} />)
    await screen.getByRole('button', { name: 'Adjust' }).click()
    await screen.getByRole('textbox', { name: 'Name' }).fill('The Grey Cough')
    await screen
      .getByRole('button', { name: 'Forge it' })
      .click({ force: true })
    await expect
      .poll(() => callsTo('POST', '/api/actions/disease:create'))
      .toHaveLength(1)
    const body = callsTo('POST', '/api/actions/disease:create')[0].body as {
      region_id: number
      name: string
      values: Record<string, unknown>
      hold: boolean
      loose_on: number | null
    }
    expect(body.region_id).toBe(7)
    expect(body.name).toBe('The Grey Cough')
    expect(body.values.primary_route).toBe('inhalation')
    expect(body.values.target_functions).toEqual(['breath'])
    expect(body.values.incubation).toBe(1)
    expect(body.hold).toBe(true)
    expect(body.loose_on).toBeNull()
  })

  it('shows how a sickness travels, what it strikes, its host and its origin', async () => {
    serve()
    onApi('GET', '/api/entities/41/disease', DISEASE)
    const { screen } = await renderApp(<DiseaseSection diseaseId={41} />)
    await expect.element(screen.getByText('How it travels')).toBeVisible()
    await expect
      .element(screen.getByText('Spreads unseen in its first age'))
      .toBeVisible()
    await expect
      .element(screen.getByText('What it strikes', { exact: true }))
      .toBeVisible()
    await expect
      .element(screen.getByText('Carried by Marsh Rats'))
      .toBeVisible()
    await expect.element(screen.getByText('Main host')).toBeVisible()
    await expect
      .element(screen.getByText(/Rose in epoch 50, year 7/))
      .toBeVisible()
    await expect.element(screen.getByText('36% unseen').first()).toBeVisible()
    await expect.element(screen.getByText('No levy').first()).toBeVisible()
  })

  it('reshapes targets, outbreaks and endemic load and releases holds', async () => {
    serve()
    onApi('GET', '/api/entities/41/disease', DISEASE)
    onApi('POST', '/api/actions/disease:edit', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/outbreak:edit', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/endemic:set', ACCEPTED_ACTION)
    const { screen } = await renderApp(<DiseaseSection diseaseId={41} />)
    await screen.getByRole('button', { name: 'Adjust' }).click()
    await screen.getByRole('button', { name: 'Sight' }).first().click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/disease:edit'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/disease:edit')[0].body).toEqual({
      disease_id: 41,
      hold: true,
      values: { target_functions: ['breath', 'cognition', 'sight'] },
    })
    await screen
      .getByRole('button', { name: 'Release struck body functions' })
      .click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/disease:edit'))
      .toHaveLength(2)
    expect(callsTo('POST', '/api/actions/disease:edit')[1].body).toEqual({
      disease_id: 41,
      hold: true,
      release: ['target_functions'],
    })
    await screen.getByRole('spinbutton', { name: 'Dead' }).fill('900')
    await screen.getByRole('button', { name: 'Set and hold' }).nth(2).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/outbreak:edit'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/outbreak:edit')[0].body).toEqual({
      outbreak_id: 3,
      hold: true,
      values: { dead: 900 },
    })
    await screen.getByRole('button', { name: 'Set its load' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/endemic:set'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/endemic:set')[0].body).toEqual({
      region_id: 7,
      disease_id: 41,
      load: 30,
      hold: true,
    })
  })

  it('shows sick and maimed cohorts and wakes, dozes, holds and sets cohorts', async () => {
    serve()
    onApi('GET', '/api/entities/30/demography', DEMOGRAPHY)
    onApi('POST', '/api/actions/mortal:dormancy', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/lever:unpin', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/cohort:set', ACCEPTED_ACTION)
    const { screen } = await renderApp(<DemographySection communityId={30} />)
    await expect
      .element(screen.getByText('The sick and the maimed'))
      .toBeVisible()
    await expect.element(screen.getByText('the marsh ague')).toBeVisible()
    await expect.element(screen.getByText('1 of 2 asleep')).toBeVisible()
    await screen.getByRole('button', { name: 'Wake' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/mortal:dormancy'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/mortal:dormancy')[0].body).toEqual({
      mortal_id: 501,
      dormant: false,
      hold: null,
    })
    await screen.getByRole('button', { name: 'Release' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/mortal:dormancy'))
      .toHaveLength(2)
    expect(callsTo('POST', '/api/actions/mortal:dormancy')[1].body).toEqual({
      mortal_id: 502,
      dormant: null,
      hold: false,
    })
    await screen.getByRole('switch', { name: 'Hold the sick' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/lever:unpin'))
      .toHaveLength(1)
    await screen.getByRole('button', { name: 'Adjust' }).click()
    await screen.getByRole('spinbutton', { name: /Headcount/ }).fill('250')
    await screen.getByRole('button', { name: 'Set the headcount' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/cohort:set'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/cohort:set')[0].body).toEqual({
      community_id: 30,
      age_band: 'adult',
      sex_kind: 'begetter',
      social_class: 'farmer',
      condition: 'none',
      count: 250,
    })
  })

  it('shows every route a sickness passes by and opens, holds and closes a further route', async () => {
    serve()
    onApi('GET', '/api/entities/41/disease', {
      ...DISEASE,
      outbreaks: [
        OUTBREAK,
        {
          ...OUTBREAK,
          id: 4,
          region: 'Lowmere',
          region_id: 8,
          path: 'waterway',
        },
      ],
    })
    onApi('POST', '/api/actions/disease_route:set', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/disease_route:remove', ACCEPTED_ACTION)
    const { screen } = await renderApp(<DiseaseSection diseaseId={41} />)
    await expect.element(screen.getByText('Thrives in wet lands')).toBeVisible()
    await expect
      .element(screen.getByText('Thrives in any warmth'))
      .toBeVisible()
    await expect.element(screen.getByText('Came downstream')).toBeVisible()
    await screen.getByRole('button', { name: 'Adjust' }).click()
    await expect.element(screen.getByText('Every way it passes')).toBeVisible()
    await expect
      .element(screen.getByText('Bites of beasts (main route)'))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Set its share' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/disease_route:set'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/disease_route:set')[0].body).toEqual({
      disease_id: 41,
      route: 'blood',
      share: 20,
      hold: false,
    })
    await screen.getByRole('button', { name: 'Close this route' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/disease_route:remove'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/disease_route:remove')[0].body
    ).toEqual({
      disease_id: 41,
      route: 'blood',
    })
  })

  it('draws the population pyramid by the sex kinds the people has', async () => {
    serve()
    onApi('GET', '/api/entities/30/demography', DEMOGRAPHY)
    const { screen } = await renderApp(<DemographySection communityId={30} />)
    await expect
      .element(
        screen.getByRole('img', {
          name: 'Population by age, sex kind and class',
        })
      )
      .toBeVisible()
    await expect
      .element(screen.getByText('Bearers', { exact: true }))
      .toBeVisible()
    await expect
      .element(screen.getByText('Begetters', { exact: true }))
      .toBeVisible()
  })
})

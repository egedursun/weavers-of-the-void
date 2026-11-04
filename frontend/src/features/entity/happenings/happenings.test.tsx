import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { EventSection } from './EventCard'
import { EventsHereSection } from './EventsHere'
import { LandShapeSection } from './LandShape'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const EVENT = {
  entity_id: 50,
  name: 'The Long Hunger',
  kind: 'famine',
  severity: 60,
  world_id: 1,
  location_id: 7,
  location: 'Vale',
  start_epoch: 40,
  start_year: 2010,
  start_season: { position: 1, name: 'Summer' },
  end_epoch: null,
  end_year: null,
  end_season: null,
  phase: 'peak',
  phase_epoch: 41,
  multi_season: true,
  ended: false,
  locked: ['phase'],
  incident_id: 3,
  incident_text: 'In the year 2010 the harvest of Vale failed.',
  siege_id: null,
  footprint: [{ region_id: 7, region: 'Vale', joined_epoch: 40 }],
  casualties: [
    {
      community_id: 9,
      community: 'Greyfield',
      age_band: 'elder',
      sex: 'female',
      social_class: 'farmer',
      phase: 'peak',
      count: 120,
    },
    {
      community_id: 9,
      community: 'Greyfield',
      age_band: 'child',
      sex: 'male',
      social_class: 'farmer',
      phase: 'peak',
      count: 80,
    },
  ],
  toll: 200,
  steps: [
    { phase: 'onset', reached: true, current: false, since_epoch: 40 },
    { phase: 'peak', reached: true, current: true, since_epoch: 41 },
    { phase: 'aftermath', reached: false, current: false, since_epoch: null },
  ],
  seasons: [{ position: 1, name: 'Summer' }],
  kinds: ['famine', 'festival_of_note'],
}

const HERE = {
  location_id: 7,
  world_id: 1,
  region_id: 7,
  events: [
    {
      entity_id: 50,
      name: 'The Long Hunger',
      kind: 'famine',
      phase: 'peak',
      ended: false,
      start_year: 2010,
      end_year: null,
      toll: 200,
      severity: 60,
    },
  ],
  kinds: ['famine', 'festival_of_note'],
  seasons: [{ position: 1, name: 'Summer' }],
}

const LAND = {
  region_id: 7,
  region: 'Vale',
  soil: 'ash',
  terrain: 'volcanic',
  river_class: 'river',
  rainfall: 30,
  grazed: 50,
  desertification: 40,
  desertified: false,
  desert_since_epoch: null,
  river_course: null,
  course_changed_epoch: null,
  volcanic: true,
  volcanic_pressure: 70,
  eruption_chance: 10.4,
  last_eruption_epoch: 39,
  ash_since_epoch: 39,
  ash_weathering_epochs: 3,
  desertified_at: 70,
  locked: ['volcanic_pressure'],
  soil_locked: false,
  shifts: [
    {
      id: 1,
      from_region_id: 7,
      from_region: 'Vale',
      to_region_id: 8,
      to_region: 'Lowmarsh',
      epoch: 30,
      year: 1500,
      river_class: 'river',
      cause: 'flood',
    },
  ],
  neighbours: [{ region_id: 8, region: 'Lowmarsh' }],
}

function serve() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 42 },
  })
  onApi('GET', '/api/names', [])
}

describe('events and the shape of the land', () => {
  beforeEach(resetApi)

  it('shows an event with its phase and toll and releases its hold', async () => {
    serve()
    onApi('GET', '/api/entities/50/event', EVENT)
    onApi('POST', '/api/actions/event:release', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/event:end', ACCEPTED_ACTION)
    const { screen } = await renderApp(<EventSection eventId={50} />)
    await expect
      .element(screen.getByText('Since the year 2010, Summer'))
      .toBeVisible()
    await expect.element(screen.getByText('Elders: 120')).toBeVisible()
    await screen.getByRole('button', { name: 'Adjust' }).click()
    await screen.getByRole('button', { name: 'Release phase' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/event:release'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/event:release')[0].body).toEqual({
      event_id: 50,
      field: 'phase',
    })
    await screen.getByRole('button', { name: 'End the event' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/event:end'))
      .toHaveLength(1)
  })

  it('lists events here and sets down a new one', async () => {
    serve()
    onApi('GET', '/api/entities/7/happenings', HERE)
    onApi('POST', '/api/actions/event:create', ACCEPTED_ACTION)
    const { screen } = await renderApp(<EventsHereSection locationId={7} />)
    await expect.element(screen.getByText('The Long Hunger')).toBeVisible()
    await screen.getByRole('button', { name: 'Adjust' }).click()
    await screen
      .getByRole('textbox', { name: 'Name' })
      .fill('The Lantern Feast')
    await screen
      .getByRole('button', { name: 'Let it come to pass' })
      .click({ force: true })
    await expect
      .poll(() => callsTo('POST', '/api/actions/event:create'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/event:create')[0].body).toMatchObject({
      kind: 'festival_of_note',
      where_id: 7,
      name: 'The Lantern Feast',
      phase: 'onset',
      hold_phase: false,
    })
  })

  it('shows the shape of the land and wakes the mountain', async () => {
    serve()
    onApi('GET', '/api/entities/7/land-shape', LAND)
    onApi('POST', '/api/actions/land:stir', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/land:release', ACCEPTED_ACTION)
    const { screen } = await renderApp(<LandShapeSection regionId={7} />)
    await expect
      .element(screen.getByText('Weathers into rich soil by age 42'))
      .toBeVisible()
    await expect
      .element(screen.getByText('River: Vale to Lowmarsh'))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Adjust' }).click()
    await screen.getByRole('button', { name: 'Let it break' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/land:stir'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/land:stir')[0].body).toEqual({
      region_id: 7,
      disaster: 'eruption',
      severity: 60,
    })
    await screen
      .getByRole('button', { name: 'Release volcanic pressure' })
      .click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/land:release'))
      .toHaveLength(1)
  })
})

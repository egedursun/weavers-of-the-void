import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { CreatePlace } from './CreatePlace'
import { PlaceSection } from './PlaceSection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const SECRET = {
  id: 3,
  kind: 'sealed_spirit',
  strength: 60,
  sealed: true,
  held: false,
  origin: 'land',
  material: null,
  school: null,
  branch: null,
  hidden_by_son_id: null,
  created_epoch: 2,
  revealed_epoch: null,
  revealed_by: null,
  revealed_by_entity_id: null,
  revealed_by_name: null,
  released_epoch: null,
  result_entity_id: null,
  result_name: null,
}

const PROFILE = {
  place_id: 12,
  kind: 'shrine_site',
  sacred_class: 'holy',
  deep: false,
  sacredness: 72,
  sacred_target: 80,
  pilgrims: 140,
  holy_site: true,
  pilgrimage_site: false,
  nexus: false,
  mystery: 40,
  mystery_held: false,
  battles: 0,
  locked: ['sacredness'],
  secrets: [SECRET],
}

function serve() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 51 },
  })
  onApi('GET', '/api/names', [])
  onApi('GET', '/api/sons', [])
}

describe('place section', () => {
  beforeEach(resetApi)

  it('shows the kind, sanctity and a hidden secret, and breaks its seal', async () => {
    serve()
    onApi('GET', '/api/places/12/profile', PROFILE)
    onApi('POST', '/api/actions/place:reveal', ACCEPTED_ACTION)
    const { screen } = await renderApp(<PlaceSection placeId={12} />)
    await expect.element(screen.getByText('Shrine site')).toBeVisible()
    await expect
      .element(screen.getByText('Hidden: sealed spirit'))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Break the seal' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/place:reveal'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/place:reveal')[0].body).toEqual({
      secret_id: 3,
      release: true,
    })
  })

  it('releases a held sacredness', async () => {
    serve()
    onApi('GET', '/api/places/12/profile', PROFILE)
    onApi('POST', '/api/actions/place:release', ACCEPTED_ACTION)
    const { screen } = await renderApp(<PlaceSection placeId={12} />)
    await screen.getByRole('button', { name: 'Release sacredness' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/place:release'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/place:release')[0].body).toEqual({
      place_id: 12,
      field: 'sacredness',
    })
  })

  it('hides a new secret in the place', async () => {
    serve()
    onApi('GET', '/api/places/12/profile', { ...PROFILE, secrets: [] })
    onApi('POST', '/api/actions/place:secret', ACCEPTED_ACTION)
    const { screen } = await renderApp(<PlaceSection placeId={12} />)
    await screen.getByRole('button', { name: 'Hide' }).click()
    await screen.getByRole('spinbutton', { name: 'Strength' }).fill('35')
    await screen.getByRole('button', { name: 'Hide it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/place:secret'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/place:secret')[0].body).toEqual({
      place_id: 12,
      kind: 'buried_relic',
      strength: 35,
      material: null,
      school: null,
      branch: null,
    })
  })

  it('brings forth a named place of a chosen kind in a region', async () => {
    serve()
    onApi('POST', '/api/actions/place:create', ACCEPTED_ACTION)
    const { screen } = await renderApp(<CreatePlace regionId={30} />)
    await screen.getByRole('button', { name: 'Create' }).click()
    await screen.getByRole('textbox', { name: 'Name' }).fill('Sunmoss')
    await screen.getByRole('button', { name: 'Bring it forth' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/place:create'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/place:create')[0].body).toEqual({
      region_id: 30,
      name: 'Sunmoss',
      kind: 'grove',
      mystery: 50,
      danger: 30,
      fertility: 50,
      sacredness: null,
    })
  })
})

import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { workshopKindValues } from '@/api/generated/schema'
import { WORKSHOP } from '@/features/entity/economy/labels'
import { POLLUTANTS } from '@/features/entity/works/labels'
import { WorksSection } from './WorksSection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const LAND = { id: 21, kind: 'entity' as const, name: 'Greenvale' }

const VIEW = {
  node_id: 21,
  name: 'Greenvale',
  community: false,
  methods: [],
  energy: [],
  stores: null,
  stocks: [],
  pollution: [],
  sites: [],
  holdings: [],
  ledger: [],
  bottlenecks: [],
  tiers: [],
}

const FOULED = {
  region: LAND,
  air: 10,
  water: 5,
  soil: 0,
  radiation: 30,
  noise: 20,
  light: 15,
  blight: 0,
  epoch: null,
  held: [],
  polluters: [],
}

function serve(view: object) {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 8 },
  })
  onApi('GET', '/api/names', [])
  onApi('GET', '/api/works/21', view)
  onApi('POST', '/api/actions/pollution:set', ACCEPTED_ACTION)
}

describe('works of batch 28', () => {
  beforeEach(resetApi)

  it('names every workshop, including the new crafts', () => {
    for (const kind of workshopKindValues)
      expect(WORKSHOP[kind].label).toBeTruthy()
  })

  it('says when no land is fouled', async () => {
    serve(VIEW)
    const { screen } = await renderApp(<WorksSection nodeId={21} />)
    await expect
      .element(
        screen.getByText(
          'No land is fouled here, or this one stands on no land.'
        )
      )
      .toBeVisible()
  })

  it('shows radiation, noise and light and sets the radiation', async () => {
    serve({ ...VIEW, pollution: [FOULED] })
    const { screen } = await renderApp(<WorksSection nodeId={21} />)
    for (const key of ['radiation', 'noise', 'light'] as const) {
      await expect
        .element(screen.getByText(POLLUTANTS[key].label).first())
        .toBeVisible()
    }
    await expect
      .element(
        screen.getByRole('button', { name: 'Wipe the record of its pollution' })
      )
      .toBeDisabled()
    await screen
      .getByRole('button', { name: 'Open how fouled the land is' })
      .click()
    await screen
      .getByRole('spinbutton', { name: new RegExp(POLLUTANTS.radiation.label) })
      .fill('45')
    await screen
      .getByRole('button', { name: `Set ${POLLUTANTS.radiation.label}` })
      .click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/pollution:set'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/pollution:set')[0].body).toMatchObject(
      {
        region_id: 21,
        radiation: 45,
      }
    )
  })
})

import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { NatureSection } from './NatureSection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const BEAR = { id: 60, kind: 'entity' as const, name: 'Snow Bear' }
const FERN = { id: 61, kind: 'entity' as const, name: 'Hook Fern' }
const LAND = { id: 5, kind: 'entity' as const, name: 'Coldmoor' }
const TOWN = { id: 40, kind: 'entity' as const, name: 'Grimsby' }

const EMPTY = {
  region: LAND,
  season_band: 'cold',
  kind_profile: null,
  folk_profile: null,
  plant: null,
  sense_holder: null,
  senses: [],
  bonds: [],
  soil: null,
  defences: [],
  cultures: [],
}

function serveBase() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 6 },
  })
  onApi('GET', '/api/names', [
    { kind: 'entity', id: 60, name: 'Snow Bear', type: 'species', world_id: 4 },
    { kind: 'entity', id: 5, name: 'Coldmoor', type: 'region', world_id: 4 },
    {
      kind: 'entity',
      id: 40,
      name: 'Grimsby',
      type: 'settlement',
      world_id: 4,
    },
  ])
}

describe('living nature', () => {
  beforeEach(() => resetApi())

  it('shows a sleeping kind, its senses and its bonds', async () => {
    serveBase()
    onApi('GET', '/api/nature/of/60', {
      ...EMPTY,
      node: BEAR,
      kind_profile: {
        dormancy: 'hibernation',
        thermoregulation: 'endotherm',
        woken_epoch: null,
        endemic: true,
        relict: false,
        island_epochs: 0,
        range_peak: 3,
        asleep_now: true,
        activity_pct: 100,
        locked: [],
      },
      sense_holder: BEAR,
      senses: [{ sense: 'smell', acuity: 70, locked: [] }],
      bonds: [
        {
          id: 2,
          first: BEAR,
          second: FERN,
          kind: 'commensalism',
          strength: 40,
          since_epoch: 3,
          locked: [],
        },
      ],
    })
    onApi('POST', '/api/actions/sense:set', ACCEPTED_ACTION)
    const { screen } = await renderApp(<NatureSection nodeId={60} />)
    await expect.element(screen.getByText('Asleep now')).toBeVisible()
    await expect
      .element(screen.getByText('Endemic', { exact: true }))
      .toBeVisible()
    await screen.getByRole('tab', { name: /Senses/ }).click()
    await expect.element(screen.getByText('Acuity 70 of 100')).toBeVisible()
    await screen.getByRole('button', { name: 'Give it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/sense:set'))
      .toHaveLength(1)
    await screen.getByRole('tab', { name: /Bonds between kinds/ }).click()
    await expect
      .element(screen.getByText('Snow Bear and Hook Fern', { exact: true }))
      .toBeVisible()
  })

  it('shows the life of a soil, its plant defences and keeps the soil control with its reason', async () => {
    serveBase()
    onApi('GET', '/api/nature/of/5', {
      ...EMPTY,
      node: LAND,
      soil: {
        life: 62,
        sterile_epochs: 0,
        updated_epoch: 6,
        recycling_pct: 115,
        locked: [],
      },
      defences: [{ defence: 'thorns', cover_pct: 40 }],
    })
    const { screen } = await renderApp(<NatureSection nodeId={5} />)
    await expect.element(screen.getByText('Thorns: 40%')).toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Set it' }))
      .toBeDisabled()
  })

  it('keeps a culture in a town and gives one', async () => {
    serveBase()
    onApi('GET', '/api/nature/of/40', {
      ...EMPTY,
      node: TOWN,
      cultures: [
        {
          id: 9,
          holder: TOWN,
          kind: 'yeast',
          quality: 45,
          since_epoch: 2,
          lost_epoch: null,
          locked: [],
        },
      ],
    })
    onApi('POST', '/api/actions/ferment_culture:create', ACCEPTED_ACTION)
    const { screen } = await renderApp(<NatureSection nodeId={40} />)
    await expect
      .element(screen.getByText('Yeast of Grimsby', { exact: true }))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Give it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/ferment_culture:create'))
      .toHaveLength(1)
  })
})

import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ClimesSection } from './ClimesSection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const WORLD = { id: 4, kind: 'world' as const, name: 'Orvael' }
const OTHER = { id: 5, kind: 'world' as const, name: 'Thessa' }
const TOWN = { id: 40, kind: 'entity' as const, name: 'Grimsby' }
const LAND = { id: 42, kind: 'entity' as const, name: 'Saltmarch' }
const ROAD = { id: 9, name: 'Orvael to Thessa by light sail' }

const EMPTY = {
  world: WORLD,
  region: LAND,
  epoch: 6,
  winds: [],
  monsoons: [],
  oscillation: null,
  windows: [],
  cultures: [],
  routes: [ROAD],
}

function serveBase() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 6 },
  })
  onApi('GET', '/api/names', [
    {
      kind: 'entity',
      id: 40,
      name: 'Grimsby',
      type: 'settlement',
      world_id: 4,
    },
    { kind: 'entity', id: 42, name: 'Saltmarch', type: 'region', world_id: 4 },
    { kind: 'world', id: 4, name: 'Orvael' },
    { kind: 'world', id: 5, name: 'Thessa' },
  ])
}

describe('winds, seasons and crossings', () => {
  beforeEach(() => resetApi())

  it('shows the wind of a land and its rain shadow, and turns it', async () => {
    serveBase()
    onApi('GET', '/api/climes/of/42', {
      ...EMPTY,
      node: LAND,
      winds: [
        {
          region: LAND,
          band: 'westerly',
          summer_band: 'doldrums',
          wind_from: 6,
          strength: 65,
          windward: false,
          shadow: 25,
          monsoon: 0,
          upwelling: true,
          read_epoch: 5,
          locked: [],
        },
      ],
    })
    onApi('POST', '/api/actions/region_wind:set', ACCEPTED_ACTION)
    const { screen } = await renderApp(<ClimesSection nodeId={42} />)
    await expect
      .element(screen.getByText('Westerly over Saltmarch'))
      .toBeVisible()
    await expect
      .element(
        screen.getByText(
          'From the west · strength 65 · in summer doldrums · read in epoch 5'
        )
      )
      .toBeVisible()
    await expect
      .element(screen.getByRole('img', { name: 'Blows from the west' }))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Set the wind' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/region_wind:set'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/region_wind:set')[0].body).toEqual({
      region_id: 42,
      band: 'trade',
      summer_band: 'trade',
      wind_from: 2,
    })
  })

  it('shows a failed monsoon and keeps the swing control with its reason', async () => {
    serveBase()
    onApi('GET', '/api/climes/of/4', {
      ...EMPTY,
      node: WORLD,
      region: null,
      monsoons: [{ epoch: 6, strength: 30, failed: true, locked: [] }],
      oscillation: {
        phase: 'warm',
        period: 6,
        step: 1,
        strength: 12,
        locked: [],
      },
    })
    const { screen } = await renderApp(<ClimesSection nodeId={4} />)
    await expect
      .element(screen.getByText('The monsoon of epoch 6', { exact: true }))
      .toBeVisible()
    await expect
      .element(screen.getByText('30% of its usual strength · failed'))
      .toBeVisible()
    await expect
      .element(screen.getByText('Climate swing: warm swing'))
      .toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Begin it' }))
      .toBeDisabled()
  })

  it('shows a window and a culture of a road with its members, and brings a town in', async () => {
    serveBase()
    onApi('GET', '/api/climes/of/40', {
      ...EMPTY,
      node: TOWN,
      windows: [
        {
          from_world: WORLD,
          to_world: OTHER,
          synodic: 4,
          offset: 1,
          open: false,
          locked: [],
        },
      ],
      cultures: [
        {
          id: 3,
          route: ROAD,
          name: 'The Folk of the Long Road',
          lingua_franca: null,
          strength: 30,
          values: [{ axis: 'tradition', value: 20 }],
          formed_epoch: 4,
          members: [
            {
              community: { id: 41, kind: 'entity', name: 'Farshore' },
              share: 40,
              joined_epoch: 4,
              locked: [],
            },
          ],
          locked: [],
        },
      ],
    })
    onApi('POST', '/api/actions/cosmopolitan_member:set', ACCEPTED_ACTION)
    const { screen } = await renderApp(<ClimesSection nodeId={40} />)
    await expect
      .element(screen.getByText('Orvael and Thessa', { exact: true }))
      .toBeVisible()
    await expect
      .element(screen.getByText('Opens every 4 epochs · opens in 1 epoch'))
      .toBeVisible()
    await expect
      .element(screen.getByText('The Folk of the Long Road').first())
      .toBeVisible()
    await expect.element(screen.getByText('Farshore')).toBeVisible()
    await screen.getByRole('button', { name: 'Bring it in' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/cosmopolitan_member:set'))
      .toHaveLength(1)
  })
})

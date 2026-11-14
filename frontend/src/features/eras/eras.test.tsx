import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { TechErasSection } from './TechErasSection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const TOWN = { id: 40, kind: 'entity' as const, name: 'Grimsby' }
const REALM = { id: 50, kind: 'entity' as const, name: 'Crown of Grimsby' }
const ORLA = { id: 32, kind: 'entity' as const, name: 'Orla' }

const STEAM = {
  technique: 'steam_power',
  label: 'Steam power',
  effect: 'Engines turn on the force of steam.',
  era: 'steam',
  held: true,
  kept: true,
  programme: false,
  requires: [],
  effects: [
    { channel: 'industry', value: 20 },
    { channel: 'pollution', value: 15 },
  ],
}
const ROCKETS = {
  technique: 'rocketry',
  label: 'Rocketry',
  effect: 'Rockets carry folk to other worlds.',
  era: 'advanced',
  held: false,
  kept: false,
  programme: true,
  requires: ['steam_power'],
  effects: [{ channel: 'world_routes', value: 20 }],
}

const BASE = {
  node: TOWN,
  realm: REALM,
  keeper: TOWN,
  era: 'steam',
  starting_era: 'iron',
  no_gunpowder: false,
  channels: [
    { channel: 'industry', value: 20 },
    { channel: 'pollution', value: 15 },
  ],
  techniques: [STEAM, ROCKETS],
  programmes: [],
}

function serveBase() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 6 },
  })
  onApi('GET', '/api/names', [
    { kind: 'entity', id: 32, name: 'Orla', type: 'mortal', world_id: 4 },
    {
      kind: 'entity',
      id: 40,
      name: 'Grimsby',
      type: 'settlement',
      world_id: 4,
    },
    {
      kind: 'entity',
      id: 50,
      name: 'Crown of Grimsby',
      type: 'polity',
      world_id: 4,
    },
  ])
}

describe('technology eras and programmes', () => {
  beforeEach(() => resetApi())

  it('shows the era a town has reached and what its techniques change', async () => {
    serveBase()
    onApi('GET', '/api/eras/of/40', BASE)
    onApi('POST', '/api/actions/eras:run', ACCEPTED_ACTION)
    const { screen } = await renderApp(<TechErasSection nodeId={40} />)
    await expect
      .element(screen.getByText('Industry: +20%', { exact: true }))
      .toBeVisible()
    await expect
      .element(screen.getByText('Pollution: +15%', { exact: true }))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Read every era now' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/eras:run'))
      .toHaveLength(1)
  })

  it('teaches a technique to the town that keeps its knowledge', async () => {
    serveBase()
    onApi('GET', '/api/eras/of/40', BASE)
    onApi('POST', '/api/actions/research:technique', ACCEPTED_ACTION)
    const { screen } = await renderApp(<TechErasSection nodeId={40} />)
    await screen.getByRole('tab', { name: /Techniques/ }).click()
    await expect
      .element(screen.getByText('Reached by a realm’s programme'))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Teach it to Grimsby' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/research:technique'))
      .toHaveLength(1)
  })

  it('shows a realm’s programme toward a technique', async () => {
    serveBase()
    onApi('GET', '/api/eras/of/50', {
      ...BASE,
      node: REALM,
      programmes: [
        {
          id: 3,
          polity: REALM,
          technique: 'rocketry',
          label: 'Rocketry',
          progress: 60,
          stage: 'building',
          visibility: 35,
          sabotaged: 1,
          started_epoch: 2,
          finished_epoch: null,
          locked: [],
        },
      ],
    })
    const { screen } = await renderApp(<TechErasSection nodeId={50} />)
    await expect
      .element(
        screen.getByText('Crown of Grimsby toward rocketry', { exact: true })
      )
      .toBeVisible()
  })

  it('keeps the begin control with its reason off a thing of no realm', async () => {
    serveBase()
    onApi('GET', '/api/eras/of/32', {
      ...BASE,
      node: ORLA,
      realm: null,
      keeper: null,
    })
    const { screen } = await renderApp(<TechErasSection nodeId={32} />)
    await screen.getByRole('tab', { name: /Programmes/ }).click()
    await expect
      .element(screen.getByRole('button', { name: 'Begin it' }))
      .toBeDisabled()
  })
})

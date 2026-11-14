import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { TalesSection } from './TalesSection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const HERO = { id: 32, kind: 'entity' as const, name: 'Orla' }
const FOE = { id: 33, kind: 'entity' as const, name: 'Varek' }
const WORLD = { id: 4, kind: 'world' as const, name: 'Orvael' }

const EMPTY = {
  formation: null,
  season: null,
  forecasts: [],
  transformations: [],
  cycle: 'linear',
  ages: [],
  echoes: [],
  arcs: [],
  setups: [],
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
    { kind: 'entity', id: 33, name: 'Varek', type: 'mortal', world_id: 4 },
    { kind: 'world', id: 4, name: 'Orvael' },
  ])
}

describe('tales, seasons and ages', () => {
  beforeEach(() => resetApi())

  it('shows a revenge tale with its foe and presses it', async () => {
    serveBase()
    onApi('GET', '/api/tales/of/32', {
      ...EMPTY,
      node: HERO,
      arcs: [
        {
          id: 7,
          subject: HERO,
          template: 'revenge',
          stage: 'rising',
          outcome: 'open',
          beats: 1,
          drama: 40,
          echo_id: null,
          started_epoch: 3,
          last_beat_epoch: 4,
          ended_epoch: null,
          figures: [{ node: FOE, role: 'foe', locked: [] }],
          history: [
            {
              id: 2,
              stage: 'rising',
              text: 'They met at the ford.',
              epoch: 4,
              locked: [],
            },
          ],
          locked: [],
        },
      ],
    })
    onApi('POST', '/api/actions/arc:press', ACCEPTED_ACTION)
    const { screen } = await renderApp(<TalesSection nodeId={32} />)
    await expect
      .element(screen.getByText('Orla: revenge, rising, drama 40'))
      .toBeVisible()
    await expect.element(screen.getByText('Foe in the tale')).toBeVisible()
    await screen
      .getByRole('button', { name: 'Press it toward its next turn' })
      .click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/arc:press'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/arc:press')[0].body).toEqual({
      arc_id: 7,
      drama: 100,
    })
  })

  it('shows a world forming and its long winter and unsettles nothing twice', async () => {
    serveBase()
    onApi('GET', '/api/tales/of/4', {
      ...EMPTY,
      node: WORLD,
      formation: {
        world: WORLD,
        zone: 'snow_line',
        migration: 'inward',
        bombardment: 60,
        craters: 4,
        core_share: 25,
        mantle_heat: 40,
        water_delivered: 70,
        exotic_delivered: 12,
        shaped: true,
        formed_epoch: 1,
        locked: [],
      },
      season: {
        world: WORLD,
        cause: 'orbit',
        spell: 'winter',
        spell_started_epoch: 5,
        spell_length: 3,
        severity: 70,
        by_node: null,
        locked: [],
      },
    })
    const { screen } = await renderApp(<TalesSection nodeId={4} />)
    await screen
      .getByRole('tab', { name: /Forming, seasons and remaking/ })
      .click()
    await expect
      .element(screen.getByText('Orvael: core 25, water 70, bombardment 60'))
      .toBeVisible()
    await expect
      .element(screen.getByText('Long winter on Orvael'))
      .toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Unsettle them' }))
      .toBeDisabled()
  })

  it('keeps the age from turning in a cosmos that runs on', async () => {
    serveBase()
    onApi('GET', '/api/tales/of/32', { ...EMPTY, node: HERO })
    const { screen } = await renderApp(<TalesSection nodeId={32} />)
    await screen.getByRole('tab', { name: /Ages and echoes/ }).click()
    await expect
      .element(screen.getByRole('button', { name: 'Turn the age now' }))
      .toBeDisabled()
  })
})

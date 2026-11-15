import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { WorldViewSection } from './WorldViewSection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const WORLD = { id: 4, kind: 'world' as const, name: 'Velmor' }
const TOWN = { id: 40, kind: 'entity' as const, name: 'Duneford' }
const NATURE = {
  light: 'star',
  need: 'water',
  settle: 'oasis',
  war: 'land',
  seasons: true,
  nights: true,
  fire: true,
  soil: true,
  timber_pct: 20,
  food_need_pct: 100,
  capacity_pct: 100,
  ore_yield_pct: 100,
  storm_pct: 100,
  quake_pct: 100,
  flood_pct: 100,
  drought_pct: 150,
  plague_pct: 100,
  route_danger: 0,
  leak: 0,
  leak_repair: 0,
  sanity_erosion: 0,
  fertility_decay: 0,
}

function serveBase() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 6 },
  })
  onApi('GET', '/api/names', [])
}

describe('world nature', () => {
  beforeEach(() => resetApi())

  it('shows what binds the towns of a world and returns it to its kind', async () => {
    serveBase()
    onApi('GET', '/api/world-views/of/40', {
      node: TOWN,
      world: WORLD,
      world_type: 'sand',
      nature: NATURE,
      kind_nature: NATURE,
      seeded: true,
      updated_epoch: 5,
      locked: [],
      absent_reason: null,
    })
    onApi('POST', '/api/actions/world_view:reset', ACCEPTED_ACTION)
    const { screen } = await renderApp(<WorldViewSection nodeId={40} />)
    await expect
      .element(screen.getByText('Towns bound to: Water'))
      .toBeVisible()
    await expect
      .element(screen.getByText('Droughts: 150%, its kind 150%'))
      .toBeVisible()
    await screen
      .getByRole('button', { name: 'Return it to the nature of its kind' })
      .click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/world_view:reset'))
      .toHaveLength(1)
  })

  it('keeps the controls on screen for a thing on no world and says why', async () => {
    serveBase()
    onApi('GET', '/api/world-views/of/1', {
      node: { id: 1, kind: 'creator', name: 'The Creator' },
      world: null,
      world_type: null,
      nature: null,
      kind_nature: null,
      seeded: false,
      updated_epoch: null,
      locked: [],
      absent_reason: 'It stands on no world.',
    })
    const { screen } = await renderApp(<WorldViewSection nodeId={1} />)
    await expect
      .element(screen.getByText('No world nature reaches this'))
      .toBeVisible()
    await expect
      .element(
        screen.getByRole('button', {
          name: 'Return it to the nature of its kind',
        })
      )
      .toBeDisabled()
  })
})

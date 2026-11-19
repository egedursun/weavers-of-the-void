import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { FossilSection } from './FossilSection'
import { GroundsSection } from './GroundsSection'
import { LifecycleSection } from './LifecycleSection'
import { WorldEndSection } from './WorldEndSection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const CREED = { id: 21, kind: 'entity' as const, name: 'The Plain Way' }
const WORLD = { id: 4, kind: 'world' as const, name: 'Velmor' }
const TOWN = { id: 40, kind: 'entity' as const, name: 'Duneford' }
const LAND = { id: 30, kind: 'entity' as const, name: 'Redmarch' }
const RIVAL = { id: 41, kind: 'entity' as const, name: 'Hollin' }
const CROWN = { id: 70, kind: 'entity' as const, name: 'Ember Crown' }
const FERN = { id: 80, kind: 'entity' as const, name: 'Bracken' }

function serveBase() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 6 },
  })
  onApi('GET', '/api/names', [])
}

describe('lifecycle ends', () => {
  beforeEach(() => resetApi())

  it('shows a dormant ideology and reads its life again', async () => {
    serveBase()
    onApi('GET', '/api/lifecycle/of/21', {
      node: CREED,
      kind: 'ideology',
      state: 'dormant',
      cause: 'no_adherents',
      idle_epochs: 1,
      grace_epochs: 1,
      since_epoch: 5,
      holders: 0,
      texts: 2,
      seeded: true,
      locked: [],
      destroy_cost: 500,
      absent_reason: null,
    })
    onApi('POST', '/api/actions/lifecycle:reset', ACCEPTED_ACTION)
    const { screen } = await renderApp(<LifecycleSection nodeId={21} />)
    await expect.element(screen.getByText('Dormant')).toBeVisible()
    await expect.element(screen.getByText('No one holds it')).toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: /Destroy for good/ }))
      .toBeDisabled()
    await screen
      .getByRole('button', { name: 'Read its life again from the world' })
      .click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/lifecycle:reset'))
      .toHaveLength(1)
  })

  it('shows a frozen world with what its end cost', async () => {
    serveBase()
    onApi('GET', '/api/world-ends/of/40', {
      node: TOWN,
      world: WORLD,
      world_type: 'ordinary',
      state: 'frozen_dead',
      cause: 'star_death',
      epoch: 6,
      former_type: 'ordinary',
      new_type: null,
      lives_ended: 1200,
      homeless: 3,
      anchors_lost: 1,
      routes_closed: 2,
      locked: [],
      end_cost: 1000,
      absent_reason: null,
    })
    const { screen } = await renderApp(<WorldEndSection nodeId={40} />)
    await expect.element(screen.getByText('1200').first()).toBeVisible()
    await expect
      .element(screen.getByText('Homeward ties cut abroad').first())
      .toBeVisible()
  })

  it('lists a hidden fossil bed and brings it to light', async () => {
    serveBase()
    onApi('GET', '/api/fossils/of/30', {
      node: LAND,
      region: LAND,
      beds: [
        {
          id: 9,
          region: LAND,
          source: 'megafauna',
          source_node: null,
          richness: 60,
          frozen: false,
          disease: null,
          laid_epoch: 3,
          found_epoch: null,
          finder: null,
          reading: 'unread',
          layer: 12,
          preservation: 'bog',
          locked: [],
        },
      ],
      world_found: 1,
      world_hidden: 2,
      absent_reason: null,
    })
    onApi('POST', '/api/actions/fossil_bed:reveal', ACCEPTED_ACTION)
    const { screen } = await renderApp(<FossilSection nodeId={30} />)
    await expect.element(screen.getByText('Great beasts').first()).toBeVisible()
    await expect.element(screen.getByText(/Kept in bog/).first()).toBeVisible()
    await screen.getByRole('button', { name: 'Bring it to light now' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/fossil_bed:reveal'))
      .toHaveLength(1)
  })

  it('gives a looted piece back from a collection and shows the gardens of a town', async () => {
    serveBase()
    onApi('GET', '/api/grounds/of/40', {
      node: TOWN,
      keeper: TOWN,
      collections: [
        {
          id: 3,
          keeper: TOWN,
          structure: null,
          kind: 'royal_collection',
          prestige: 12,
          founded_epoch: 2,
          pieces: [
            {
              id: 5,
              kind: 'artifact',
              item: CROWN,
              fossil_bed_id: null,
              acquired_epoch: 5,
              looted_from: RIVAL,
              returned_epoch: null,
              returned_by: null,
              locked: [],
            },
          ],
          locked: [],
        },
      ],
      gardens: [
        {
          id: 7,
          town: TOWN,
          structure: null,
          kind: 'physic',
          species: [FERN],
          upkeep: 10,
          condition: 65,
          unpaid_epochs: 0,
          founded_epoch: 4,
          locked: [],
        },
      ],
      absent_reason: null,
    })
    onApi('POST', '/api/actions/museum_piece:restitute', ACCEPTED_ACTION)
    const { screen } = await renderApp(<GroundsSection nodeId={40} />)
    await expect.element(screen.getByText('Taken from Hollin')).toBeVisible()
    await expect
      .element(screen.getByText('Physic garden').first())
      .toBeVisible()
    await screen.getByRole('button', { name: 'Give it back' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/museum_piece:restitute'))
      .toHaveLength(1)
  })
})

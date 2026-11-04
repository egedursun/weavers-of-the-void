import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AnchorageSection } from './AnchorageSection'
import { DedicationSection } from './DedicationSection'
import { GoldenAgeSection } from './GoldenAgeCard'
import { battles } from './labels'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const TEMPLE = { id: 78, kind: 'entity', name: 'Hesmara Sekisi' }
const SPRING = { id: 42, kind: 'entity', name: 'Sehlamir' }

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

describe('foundation sections', () => {
  beforeEach(resetApi)

  it('reads a golden age and holds its date', async () => {
    serve()
    onApi('GET', '/api/worlds/4/golden-age', {
      world_id: 4,
      active: true,
      since_epoch: 3,
      epochs: 48,
      prosperity_gain: 4,
      decadence: 1,
      held: false,
      communities: 75,
      golden_communities: 75,
      deepening_epochs: 2,
      deepening_steps: 3,
      decadence_epochs: 8,
    })
    onApi('POST', '/api/actions/world:date_golden_age', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/foundation:hold', ACCEPTED_ACTION)
    const { screen } = await renderApp(<GoldenAgeSection worldId={4} />)
    await expect.element(screen.getByText('Age 3')).toBeVisible()
    await expect
      .element(screen.getByText('Warriors and walls lose 1 each age'))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Shape the age' }).click()
    await screen.getByRole('spinbutton', { name: 'Began in age' }).fill('5')
    await screen.getByRole('button', { name: 'Set the date' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/world:date_golden_age'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/world:date_golden_age')[0].body
    ).toEqual({ world_id: 4, since_epoch: 5, hold: true })
    await screen
      .getByRole('switch', { name: 'Hold the golden age' })
      .nth(1)
      .click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/foundation:hold'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/foundation:hold')[0].body).toEqual({
      kind: 'golden_age',
      node_id: 4,
      held: true,
    })
  })

  it('shows a god’s anchor, shrines and wars and cuts the anchor', async () => {
    serve()
    onApi('GET', '/api/sons/11/anchorage', {
      son_id: 11,
      anchor: SPRING,
      anchor_alive: true,
      anchor_held: true,
      shrines: [TEMPLE],
      creations: [SPRING],
      incited: [
        {
          war_id: 100,
          event: { id: 3892, kind: 'entity', name: 'War of the Reeds' },
          status: 'ongoing',
          ending: null,
          started_epoch: 48,
          ended_epoch: null,
          battles: 1,
          held: true,
        },
      ],
    })
    onApi('POST', '/api/actions/son:clear_anchor', ACCEPTED_ACTION)
    const { screen } = await renderApp(
      <AnchorageSection sonId={11} name='Selon' />
    )
    await expect.element(screen.getByText('War of the Reeds')).toBeVisible()
    await expect
      .element(screen.getByText('Begun in age 48 · Still burning · 1 battle'))
      .toBeVisible()
    await expect.element(screen.getByText('The anchor is held')).toBeVisible()
    await screen.getByRole('button', { name: 'Move the anchor' }).click()
    await screen.getByRole('button', { name: 'Cut the anchor' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/son:clear_anchor'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/son:clear_anchor')[0].body).toEqual({
      son_id: 11,
    })
  })

  it('lifts a structure’s dedication', async () => {
    serve()
    onApi('GET', '/api/entities/78/dedication', {
      structure_id: 78,
      son: { id: 11, kind: 'son', name: 'Selon' },
      held: false,
      anchors_son: true,
    })
    onApi('POST', '/api/actions/structure:undedicate', ACCEPTED_ACTION)
    const { screen } = await renderApp(<DedicationSection structureId={78} />)
    await expect.element(screen.getByText('Their anchor')).toBeVisible()
    await screen.getByRole('button', { name: 'Dedicate' }).first().click()
    await screen.getByRole('button', { name: 'Lift the dedication' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/structure:undedicate'))
      .toHaveLength(1)
    expect(battles(2)).toBe('2 battles')
  })
})

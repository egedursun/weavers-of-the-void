import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { TreatySection } from './HouseTreaty'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const TREATY = {
  id: 7,
  name: 'Accord of the Two Shores',
  kind: 'peace',
  status: 'in_force',
  signed_epoch: 4,
  until_epoch: null,
  ended_epoch: null,
  witness_son_id: null,
  renewals: 0,
  parties: [
    { id: 40, name: 'Varo', role: 'signatory' },
    { id: 41, name: 'Ostra', role: 'signatory' },
  ],
  clauses: [
    {
      id: 3,
      kind: 'fleet_limit',
      obligor_id: 40,
      obligor: 'Varo',
      beneficiary_id: 41,
      beneficiary: 'Ostra',
      params: { amount: 300, frame: 'galleon' },
      last_kept_epoch: null,
      locked: [],
    },
  ],
  breaches: [],
  locked: [],
  proposed_by_id: null,
}

describe('a treaty’s fleet limits', () => {
  beforeEach(() => resetApi())

  it('names the class of ship a limit counts and writes in a limit on one class', async () => {
    onApi('GET', '/api/state', {
      creator: { essence: 500 },
      epoch_running: false,
      read_only: false,
      world: { epoch: 6 },
    })
    onApi('GET', '/api/names', [
      { kind: 'entity', id: 40, name: 'Varo', type: 'polity', world_id: 1 },
      { kind: 'entity', id: 41, name: 'Ostra', type: 'polity', world_id: 1 },
    ])
    onApi('GET', '/api/treaties/7', TREATY)
    onApi('GET', '/api/vehicles/frames', [
      { frame: 'galleon', label: 'Galleon', family: 'sailing_ship' },
      { frame: 'frigate', label: 'Frigate', family: 'sailing_ship' },
    ])
    onApi('POST', '/api/actions/treaty:clause_add', ACCEPTED_ACTION)
    const { screen } = await renderApp(<TreatySection treatyId={7} />)
    await expect
      .element(screen.getByText('Tonnage: 300 · Class of ship: Galleon'))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Add a clause' }).click()
    await screen
      .getByRole('group', { name: 'Clause' })
      .getByRole('button', { name: /Fleet limit/ })
      .click()
    await screen.getByRole('combobox', { name: 'Class of ship' }).click()
    await screen.getByRole('option', { name: 'Frigate' }).click()
    await screen.getByRole('button', { name: 'Write it in' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/treaty:clause_add'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/treaty:clause_add')[0].body
    ).toMatchObject({
      treaty_id: 7,
      kind: 'fleet_limit',
      params: { amount: 100, frame: 'frigate' },
    })
  })
})

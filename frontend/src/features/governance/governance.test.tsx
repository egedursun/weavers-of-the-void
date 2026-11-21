import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { GovernanceSection } from './GovernanceSection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const column = (name: string, kind: string, extra = {}) => ({
  name,
  kind,
  options: [],
  nullable: false,
  primary: false,
  owner: false,
  required: false,
  editable: true,
  ...extra,
})

const bids = {
  table: 'org_mergers',
  label: 'Org mergers',
  columns: [
    column('acquirer_node_id', 'integer', { owner: true, editable: false }),
    column('kind', 'choice', {
      options: ['merger', 'hostile_takeover'],
    }),
    column('price', 'integer'),
    column('stage', 'choice', { options: ['bid', 'agreed', 'closed'] }),
  ],
  rows: [
    {
      key: { id: 3 },
      values: { acquirer_node_id: 7, kind: 'merger', price: 50, stage: 'bid' },
      held: [],
    },
    {
      key: { id: 4 },
      values: {
        acquirer_node_id: 7,
        kind: 'hostile_takeover',
        price: 90,
        stage: 'closed',
      },
      held: [],
    },
  ],
}

const tags = {
  table: 'entity_tags',
  label: 'Entity tags',
  columns: [column('tag', 'text')],
  rows: [{ key: { entity_id: 7, tag: 'x' }, values: { tag: 'x' }, held: [] }],
}

describe('governance section', () => {
  beforeEach(() => resetApi())

  it('shows only the records of governance and carries an open bid a stage further', async () => {
    onApi('GET', '/api/records/7/rows', {
      node_id: 7,
      tables: [bids, tags],
      creatable: [bids, tags],
      names: {},
    })
    onApi('POST', '/api/actions/org_merger:advance', ACCEPTED_ACTION)
    const { screen } = await renderApp(<GovernanceSection nodeId={7} />)
    await expect
      .element(screen.getByText('Governance', { exact: true }))
      .toBeVisible()
    expect(
      screen.getByRole('button', { name: 'Open entity tags' }).query()
    ).toBeNull()
    await screen.getByRole('button', { name: 'Open org mergers' }).click()
    const steps = screen.getByRole('button', {
      name: 'Carry this bid a stage further',
    })
    await expect.element(steps.nth(1)).toBeDisabled()
    await steps.nth(0).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/org_merger:advance'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/org_merger:advance')[0].body).toEqual({
      record_id: 3,
    })
  })
})

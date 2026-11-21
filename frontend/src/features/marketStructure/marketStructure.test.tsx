import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MarketStructureSection } from './MarketStructureSection'

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

const compacts = {
  table: 'cartels',
  label: 'Cartels',
  columns: [
    column('leader_node_id', 'integer', { owner: true, editable: false }),
    column('aim', 'choice', { options: ['price', 'quota'] }),
    column('discipline', 'integer'),
  ],
  rows: [
    {
      key: { id: 5 },
      values: { leader_node_id: 7, aim: 'price', discipline: 60 },
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

describe('market structure section', () => {
  beforeEach(() => resetApi())

  it('shows only the records of the market and strikes a compact by its own lever', async () => {
    onApi('GET', '/api/records/7/rows', {
      node_id: 7,
      tables: [compacts, tags],
      creatable: [compacts, tags],
      names: {},
    })
    onApi('POST', '/api/actions/cartel:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<MarketStructureSection nodeId={7} />)
    await expect
      .element(screen.getByText('Market structure', { exact: true }))
      .toBeVisible()
    expect(
      screen.getByRole('button', { name: 'Open entity tags' }).query()
    ).toBeNull()
    await screen.getByRole('button', { name: 'Open cartels' }).click()
    await screen.getByRole('button', { name: 'Unmake this row' }).click()
    await screen.getByRole('button', { name: 'Unmake it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/cartel:delete'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/cartel:delete')[0].body).toEqual({
      table: 'cartels',
      key: { id: 5 },
    })
  })
})

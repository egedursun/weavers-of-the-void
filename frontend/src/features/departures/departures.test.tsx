import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { DeparturesSection } from './DeparturesSection'

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

const leavings = {
  table: 'departures',
  label: 'Departures',
  columns: [
    column('holder_node_id', 'integer', { owner: true, editable: false }),
    column('kind', 'choice', { options: ['abdication', 'retirement'] }),
    column('standing', 'integer'),
  ],
  rows: [
    {
      key: { id: 5 },
      values: { holder_node_id: 7, kind: 'abdication', standing: 60 },
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

describe('departures section', () => {
  beforeEach(() => resetApi())

  it('shows only the records of leaving office and strikes one by its own lever', async () => {
    onApi('GET', '/api/records/7/rows', {
      node_id: 7,
      tables: [leavings, tags],
      creatable: [leavings, tags],
      names: {},
    })
    onApi('POST', '/api/actions/departure:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<DeparturesSection nodeId={7} />)
    await expect
      .element(screen.getByText('Leaving office', { exact: true }))
      .toBeVisible()
    expect(
      screen.getByRole('button', { name: 'Open entity tags' }).query()
    ).toBeNull()
    await screen.getByRole('button', { name: 'Open departures' }).click()
    await screen.getByRole('button', { name: 'Unmake this row' }).click()
    await screen.getByRole('button', { name: 'Unmake it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/departure:delete'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/departure:delete')[0].body).toEqual({
      table: 'departures',
      key: { id: 5 },
    })
  })
})

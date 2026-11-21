import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ReckoningSection } from './ReckoningSection'

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

const cases = {
  table: 'reckoning_cases',
  label: 'Reckoning cases',
  columns: [
    column('accused_node_id', 'integer', { owner: true, editable: false }),
    column('outcome', 'choice', { options: ['pending', 'convicted'] }),
    column('epoch', 'integer'),
  ],
  rows: [
    {
      key: { id: 5 },
      values: { accused_node_id: 7, outcome: 'pending', epoch: 60 },
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

describe('reckoning section', () => {
  beforeEach(() => resetApi())

  it('shows only the records of a reckoning and strikes a case by its own lever', async () => {
    onApi('GET', '/api/records/7/rows', {
      node_id: 7,
      tables: [cases, tags],
      creatable: [cases, tags],
      names: {},
    })
    onApi('POST', '/api/actions/reckoning_case:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<ReckoningSection nodeId={7} />)
    await expect
      .element(screen.getByText('Reckoning', { exact: true }))
      .toBeVisible()
    expect(
      screen.getByRole('button', { name: 'Open entity tags' }).query()
    ).toBeNull()
    await screen.getByRole('button', { name: 'Open reckoning cases' }).click()
    await screen.getByRole('button', { name: 'Unmake this row' }).click()
    await screen.getByRole('button', { name: 'Unmake it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/reckoning_case:delete'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/reckoning_case:delete')[0].body
    ).toEqual({
      table: 'reckoning_cases',
      key: { id: 5 },
    })
  })
})

import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { EndowmentsSection } from './EndowmentsSection'

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

const care = {
  table: 'endowments',
  label: 'Endowments',
  columns: [
    column('founder_node_id', 'integer', {
      owner: true,
      editable: false,
    }),
    column('purpose', 'choice', {
      options: ['relief', 'learning', 'worship'],
    }),
    column('capital', 'integer'),
  ],
  rows: [
    {
      key: { id: 3 },
      values: { founder_node_id: 7, purpose: 'relief', capital: 120 },
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

describe('endowments section', () => {
  beforeEach(() => resetApi())

  it('shows only endowments and strikes one by its own lever', async () => {
    onApi('GET', '/api/records/7/rows', {
      node_id: 7,
      tables: [care, tags],
      creatable: [care, tags],
      names: {},
    })
    onApi('POST', '/api/actions/endowment:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<EndowmentsSection nodeId={7} />)
    await expect
      .element(screen.getByText('Endowments', { exact: true }))
      .toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Open endowments' }))
      .toBeVisible()
    expect(
      screen.getByRole('button', { name: 'Open entity tags' }).query()
    ).toBeNull()
    await screen.getByRole('button', { name: 'Open endowments' }).click()
    await screen.getByRole('button', { name: 'Unmake this row' }).click()
    await screen.getByRole('button', { name: 'Unmake it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/endowment:delete'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/endowment:delete')[0].body).toEqual({
      table: 'endowments',
      key: { id: 3 },
    })
  })
})

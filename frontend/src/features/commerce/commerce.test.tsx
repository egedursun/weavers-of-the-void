import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { CommerceSection } from './CommerceSection'

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
  table: 'shops',
  label: 'Shops',
  columns: [
    column('keeper_node_id', 'integer', {
      owner: true,
      editable: false,
    }),
    column('form', 'choice', {
      options: ['stall', 'shop', 'peddler'],
    }),
    column('margin', 'integer'),
  ],
  rows: [
    {
      key: { id: 3 },
      values: { keeper_node_id: 7, form: 'stall', margin: 20 },
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

describe('commerce section', () => {
  beforeEach(() => resetApi())

  it('shows only the records of commerce and strikes them by their own lever', async () => {
    onApi('GET', '/api/records/7/rows', {
      node_id: 7,
      tables: [care, tags],
      creatable: [care, tags],
      names: {},
    })
    onApi('POST', '/api/actions/shop:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<CommerceSection nodeId={7} />)
    await expect
      .element(screen.getByText('Commerce', { exact: true }))
      .toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Open shops' }))
      .toBeVisible()
    expect(
      screen.getByRole('button', { name: 'Open entity tags' }).query()
    ).toBeNull()
    await screen.getByRole('button', { name: 'Open shops' }).click()
    await screen.getByRole('button', { name: 'Unmake this row' }).click()
    await screen.getByRole('button', { name: 'Unmake it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/shop:delete'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/shop:delete')[0].body).toEqual({
      table: 'shops',
      key: { id: 3 },
    })
  })
})

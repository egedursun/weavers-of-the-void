import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { WaterIceSection } from './WaterIceSection'

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

const rows = {
  table: 'coasts',
  label: 'Coasts',
  columns: [
    column('region_entity_id', 'integer', {
      owner: true,
      editable: false,
    }),
    column('form', 'choice', { options: ['delta', 'cliff'] }),
    column('harbour_silting', 'integer'),
  ],
  rows: [
    {
      key: { region_entity_id: 7 },
      values: { region_entity_id: 7, form: 'delta', harbour_silting: 40 },
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

describe('the water, ice and sediment section', () => {
  beforeEach(() => resetApi())

  it('shows only its own records and strikes one by its own lever', async () => {
    onApi('GET', '/api/records/7/rows', {
      node_id: 7,
      tables: [rows, tags],
      creatable: [rows, tags],
      names: {},
    })
    onApi('POST', '/api/actions/coast:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<WaterIceSection nodeId={7} />)
    await expect
      .element(screen.getByText('Water, ice and sediment', { exact: true }))
      .toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Open coasts' }))
      .toBeVisible()
    expect(
      screen.getByRole('button', { name: 'Open entity tags' }).query()
    ).toBeNull()
    await screen.getByRole('button', { name: 'Open coasts' }).click()
    await screen.getByRole('button', { name: 'Unmake this row' }).click()
    await screen.getByRole('button', { name: 'Unmake it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/coast:delete'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/coast:delete')[0].body).toEqual({
      table: 'coasts',
      key: { region_entity_id: 7 },
    })
  })
})

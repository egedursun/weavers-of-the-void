import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { GraveGoodsSection } from './GraveGoodsSection'

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

const graves = {
  table: 'grave_goods',
  label: 'Grave goods',
  columns: [
    column('dead_entity_id', 'integer', { owner: true, editable: false }),
    column('guard', 'choice', { options: ['none', 'sealed'] }),
    column('goods_value', 'integer'),
  ],
  rows: [
    {
      key: { id: 5 },
      values: { dead_entity_id: 7, guard: 'sealed', goods_value: 60 },
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

describe('grave goods section', () => {
  beforeEach(() => resetApi())

  it('shows only the goods of the graves and strikes one by its own lever', async () => {
    onApi('GET', '/api/records/7/rows', {
      node_id: 7,
      tables: [graves, tags],
      creatable: [graves, tags],
      names: {},
    })
    onApi('POST', '/api/actions/grave_good:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<GraveGoodsSection nodeId={7} />)
    await expect
      .element(screen.getByText('Grave goods', { exact: true }))
      .toBeVisible()
    expect(
      screen.getByRole('button', { name: 'Open entity tags' }).query()
    ).toBeNull()
    await screen.getByRole('button', { name: 'Open grave goods' }).click()
    await screen.getByRole('button', { name: 'Unmake this row' }).click()
    await screen.getByRole('button', { name: 'Unmake it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/grave_good:delete'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/grave_good:delete')[0].body).toEqual({
      table: 'grave_goods',
      key: { id: 5 },
    })
  })
})

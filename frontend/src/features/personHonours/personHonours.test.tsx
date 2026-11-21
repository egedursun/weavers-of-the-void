import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { PersonHonoursSection } from './PersonHonoursSection'

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

const kinds = {
  table: 'honour_kinds',
  label: 'Honour kinds',
  columns: [
    column('conferrer_node_id', 'integer', { owner: true, editable: false }),
    column('hereditary', 'boolean'),
    column('rank', 'integer'),
  ],
  rows: [
    {
      key: { id: 5 },
      values: { conferrer_node_id: 7, hereditary: true, rank: 2 },
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

describe('person honours section', () => {
  beforeEach(() => resetApi())

  it('shows only the honours and strikes one by its own lever', async () => {
    onApi('GET', '/api/records/7/rows', {
      node_id: 7,
      tables: [kinds, tags],
      creatable: [kinds, tags],
      names: {},
    })
    onApi('POST', '/api/actions/honour_kind:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<PersonHonoursSection nodeId={7} />)
    await expect
      .element(screen.getByText('Honours', { exact: true }))
      .toBeVisible()
    expect(
      screen.getByRole('button', { name: 'Open entity tags' }).query()
    ).toBeNull()
    await screen.getByRole('button', { name: 'Open honour kinds' }).click()
    await screen.getByRole('button', { name: 'Unmake this row' }).click()
    await screen.getByRole('button', { name: 'Unmake it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/honour_kind:delete'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/honour_kind:delete')[0].body).toEqual({
      table: 'honour_kinds',
      key: { id: 5 },
    })
  })
})

import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { FamilySection } from './FamilySection'

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

const rivalries = {
  table: 'kin_rivalries',
  label: 'Kin rivalries',
  columns: [
    column('first_node_id', 'integer', { owner: true, editable: false }),
    column('cause', 'choice', { options: ['favour', 'love'] }),
    column('heat', 'integer'),
  ],
  rows: [
    {
      key: { id: 5 },
      values: { first_node_id: 7, cause: 'love', heat: 60 },
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

describe('family section', () => {
  beforeEach(() => resetApi())

  it('shows only the records of a family and strikes a rivalry by its own lever', async () => {
    onApi('GET', '/api/records/7/rows', {
      node_id: 7,
      tables: [rivalries, tags],
      creatable: [rivalries, tags],
      names: {},
    })
    onApi('POST', '/api/actions/kin_rivalry:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<FamilySection nodeId={7} />)
    await expect
      .element(screen.getByText('Family', { exact: true }))
      .toBeVisible()
    expect(
      screen.getByRole('button', { name: 'Open entity tags' }).query()
    ).toBeNull()
    await screen.getByRole('button', { name: 'Open kin rivalries' }).click()
    await screen.getByRole('button', { name: 'Unmake this row' }).click()
    await screen.getByRole('button', { name: 'Unmake it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/kin_rivalry:delete'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/kin_rivalry:delete')[0].body).toEqual({
      table: 'kin_rivalries',
      key: { id: 5 },
    })
  })
})

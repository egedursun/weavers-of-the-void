import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { YouthSection } from './YouthSection'

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
  table: 'youth_groups',
  label: 'Youth groups',
  columns: [
    column('settlement_entity_id', 'integer', {
      owner: true,
      editable: false,
    }),
    column('purpose', 'choice', {
      options: ['sport', 'service', 'defence'],
    }),
    column('standing', 'integer'),
  ],
  rows: [
    {
      key: { id: 3 },
      values: { settlement_entity_id: 7, purpose: 'sport', standing: 60 },
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

describe('youth section', () => {
  beforeEach(() => resetApi())

  it('shows only the records of youth and strikes them by their own lever', async () => {
    onApi('GET', '/api/records/7/rows', {
      node_id: 7,
      tables: [care, tags],
      creatable: [care, tags],
      names: {},
    })
    onApi('POST', '/api/actions/youth_group:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<YouthSection nodeId={7} />)
    await expect
      .element(screen.getByText('Youth', { exact: true }))
      .toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Open youth groups' }))
      .toBeVisible()
    expect(
      screen.getByRole('button', { name: 'Open entity tags' }).query()
    ).toBeNull()
    await screen.getByRole('button', { name: 'Open youth groups' }).click()
    await screen.getByRole('button', { name: 'Unmake this row' }).click()
    await screen.getByRole('button', { name: 'Unmake it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/youth_group:delete'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/youth_group:delete')[0].body).toEqual({
      table: 'youth_groups',
      key: { id: 3 },
    })
  })
})

import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { FolkKnowledgeSection } from './FolkKnowledgeSection'

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
  table: 'folk_classes',
  label: 'Folk classes',
  columns: [
    column('people_entity_id', 'integer', {
      owner: true,
      editable: false,
    }),
    column('taken_as', 'choice', {
      options: ['food', 'poison', 'harmless'],
    }),
    column('name', 'text'),
  ],
  rows: [
    {
      key: { id: 3 },
      values: { people_entity_id: 7, taken_as: 'food', name: 'Bitter Sedge' },
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

describe('folk knowledge section', () => {
  beforeEach(() => resetApi())

  it('shows only what a people knows and strikes a class by its own lever', async () => {
    onApi('GET', '/api/records/7/rows', {
      node_id: 7,
      tables: [care, tags],
      creatable: [care, tags],
      names: {},
    })
    onApi('POST', '/api/actions/folk_class:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<FolkKnowledgeSection nodeId={7} />)
    await expect
      .element(screen.getByText('What they know', { exact: true }))
      .toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Open folk classes' }))
      .toBeVisible()
    expect(
      screen.getByRole('button', { name: 'Open entity tags' }).query()
    ).toBeNull()
    await screen.getByRole('button', { name: 'Open folk classes' }).click()
    await screen.getByRole('button', { name: 'Unmake this row' }).click()
    await screen.getByRole('button', { name: 'Unmake it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/folk_class:delete'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/folk_class:delete')[0].body).toEqual({
      table: 'folk_classes',
      key: { id: 3 },
    })
  })
})

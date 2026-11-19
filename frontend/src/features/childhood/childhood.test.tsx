import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ChildhoodSection } from './ChildhoodSection'

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
  table: 'pedagogy',
  label: 'Pedagogy',
  columns: [
    column('holder_node_id', 'integer', {
      owner: true,
      editable: false,
    }),
    column('theory', 'choice', {
      options: ['rote', 'dialectic', 'discovery'],
    }),
    column('depth', 'integer'),
  ],
  rows: [
    {
      key: { id: 3 },
      values: { holder_node_id: 7, theory: 'dialectic', depth: 70 },
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

describe('childhood section', () => {
  beforeEach(() => resetApi())

  it('shows only the records of childhood and strikes them by their own lever', async () => {
    onApi('GET', '/api/records/7/rows', {
      node_id: 7,
      tables: [care, tags],
      creatable: [care, tags],
      names: {},
    })
    onApi('POST', '/api/actions/pedagogy:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<ChildhoodSection nodeId={7} />)
    await expect
      .element(screen.getByText('Childhood', { exact: true }))
      .toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Open pedagogy' }))
      .toBeVisible()
    expect(
      screen.getByRole('button', { name: 'Open entity tags' }).query()
    ).toBeNull()
    await screen.getByRole('button', { name: 'Open pedagogy' }).click()
    await screen.getByRole('button', { name: 'Unmake this row' }).click()
    await screen.getByRole('button', { name: 'Unmake it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/pedagogy:delete'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/pedagogy:delete')[0].body).toEqual({
      table: 'pedagogy',
      key: { id: 3 },
    })
  })
})

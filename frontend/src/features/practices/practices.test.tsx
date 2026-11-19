import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { PracticesSection } from './PracticesSection'

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

const roles = {
  table: 'facet_practices',
  label: 'Facet practices',
  columns: [
    column('community_entity_id', 'integer', {
      owner: true,
      editable: false,
    }),
    column('facet', 'choice', {
      options: ['masonry', 'computing', 'clans'],
    }),
    column('level', 'integer'),
  ],
  rows: [
    {
      key: { id: 3 },
      values: { community_entity_id: 7, facet: 'masonry', level: 60 },
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

describe('the practices section', () => {
  beforeEach(() => resetApi())

  it('shows only the practices and strikes one by its own lever', async () => {
    onApi('GET', '/api/records/7/rows', {
      node_id: 7,
      tables: [roles, tags],
      creatable: [roles, tags],
      names: {},
    })
    onApi('POST', '/api/actions/facet_practice:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<PracticesSection nodeId={7} />)
    await expect
      .element(screen.getByText('Practices', { exact: true }))
      .toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Open facet practices' }))
      .toBeVisible()
    expect(
      screen.getByRole('button', { name: 'Open entity tags' }).query()
    ).toBeNull()
    await screen.getByRole('button', { name: 'Open facet practices' }).click()
    await screen.getByRole('button', { name: 'Unmake this row' }).click()
    await screen.getByRole('button', { name: 'Unmake it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/facet_practice:delete'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/facet_practice:delete')[0].body
    ).toEqual({
      table: 'facet_practices',
      key: { id: 3 },
    })
  })
})

import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MediaSection } from './MediaSection'

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
  table: 'media_outlets',
  label: 'Media outlets',
  columns: [
    column('owner_node_id', 'integer', {
      owner: true,
      editable: false,
    }),
    column('funding', 'choice', {
      options: ['sales', 'patronage', 'state'],
    }),
    column('trust', 'integer'),
  ],
  rows: [
    {
      key: { id: 3 },
      values: { owner_node_id: 7, funding: 'sales', trust: 60 },
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

describe('media section', () => {
  beforeEach(() => resetApi())

  it('shows only the records of media and strikes them by their own lever', async () => {
    onApi('GET', '/api/records/7/rows', {
      node_id: 7,
      tables: [care, tags],
      creatable: [care, tags],
      names: {},
    })
    onApi('POST', '/api/actions/media_outlet:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<MediaSection nodeId={7} />)
    await expect
      .element(screen.getByText('Media', { exact: true }))
      .toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Open media outlets' }))
      .toBeVisible()
    expect(
      screen.getByRole('button', { name: 'Open entity tags' }).query()
    ).toBeNull()
    await screen.getByRole('button', { name: 'Open media outlets' }).click()
    await screen.getByRole('button', { name: 'Unmake this row' }).click()
    await screen.getByRole('button', { name: 'Unmake it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/media_outlet:delete'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/media_outlet:delete')[0].body).toEqual(
      {
        table: 'media_outlets',
        key: { id: 3 },
      }
    )
  })
})

import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { SpaceWeatherSection } from './SpaceWeatherSection'

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
  table: 'world_fields',
  label: 'World fields',
  columns: [
    column('world_id', 'integer', {
      owner: true,
      editable: false,
    }),
    column('shielding', 'integer'),
    column('compass_error', 'integer'),
  ],
  rows: [
    {
      key: { world_id: 7 },
      values: { world_id: 7, shielding: 50, compass_error: 12 },
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

describe('the fields and space weather section', () => {
  beforeEach(() => resetApi())

  it('shows only its own records and strikes one by its own lever', async () => {
    onApi('GET', '/api/records/7/rows', {
      node_id: 7,
      tables: [rows, tags],
      creatable: [rows, tags],
      names: {},
    })
    onApi('POST', '/api/actions/world_field:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<SpaceWeatherSection nodeId={7} />)
    await expect
      .element(screen.getByText('Fields and space weather', { exact: true }))
      .toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Open world fields' }))
      .toBeVisible()
    expect(
      screen.getByRole('button', { name: 'Open entity tags' }).query()
    ).toBeNull()
    await screen.getByRole('button', { name: 'Open world fields' }).click()
    await screen.getByRole('button', { name: 'Unmake this row' }).click()
    await screen.getByRole('button', { name: 'Unmake it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/world_field:delete'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/world_field:delete')[0].body).toEqual({
      table: 'world_fields',
      key: { world_id: 7 },
    })
  })
})

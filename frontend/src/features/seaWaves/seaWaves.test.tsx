import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { SeaWavesSection } from './SeaWavesSection'

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

const waves = {
  table: 'sea_waves',
  label: 'Sea waves',
  columns: [
    column('world_id', 'integer', { owner: true, editable: false }),
    column('origin', 'choice', { options: ['quake', 'storm'] }),
    column('strength', 'integer'),
  ],
  rows: [
    {
      key: { id: 5 },
      values: { world_id: 7, origin: 'quake', strength: 60 },
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

describe('sea waves section', () => {
  beforeEach(() => resetApi())

  it('shows only the waves and strikes one by its own lever', async () => {
    onApi('GET', '/api/records/7/rows', {
      node_id: 7,
      tables: [waves, tags],
      creatable: [waves, tags],
      names: {},
    })
    onApi('POST', '/api/actions/sea_wave:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<SeaWavesSection nodeId={7} />)
    await expect
      .element(screen.getByText('Sea waves', { exact: true }))
      .toBeVisible()
    expect(
      screen.getByRole('button', { name: 'Open entity tags' }).query()
    ).toBeNull()
    await screen.getByRole('button', { name: 'Open sea waves' }).click()
    await screen.getByRole('button', { name: 'Unmake this row' }).click()
    await screen.getByRole('button', { name: 'Unmake it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/sea_wave:delete'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/sea_wave:delete')[0].body).toEqual({
      table: 'sea_waves',
      key: { id: 5 },
    })
  })
})

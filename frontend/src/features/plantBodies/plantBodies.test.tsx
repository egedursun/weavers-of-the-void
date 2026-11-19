import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { PlantBodiesSection } from './PlantBodiesSection'

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
  table: 'plant_anatomy',
  label: 'Plant anatomy',
  columns: [
    column('species_entity_id', 'integer', {
      owner: true,
      editable: false,
    }),
    column('form', 'choice', { options: ['tree', 'herb'] }),
    column('lifespan_years', 'integer'),
  ],
  rows: [
    {
      key: { species_entity_id: 7 },
      values: { species_entity_id: 7, form: 'tree', lifespan_years: 200 },
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

describe('the plant bodies section', () => {
  beforeEach(() => resetApi())

  it('shows only its own records and strikes one by its own lever', async () => {
    onApi('GET', '/api/records/7/rows', {
      node_id: 7,
      tables: [rows, tags],
      creatable: [rows, tags],
      names: {},
    })
    onApi('POST', '/api/actions/plant_anatomy:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<PlantBodiesSection nodeId={7} />)
    await expect
      .element(screen.getByText('Plant bodies', { exact: true }))
      .toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Open plant anatomy' }))
      .toBeVisible()
    expect(
      screen.getByRole('button', { name: 'Open entity tags' }).query()
    ).toBeNull()
    await screen.getByRole('button', { name: 'Open plant anatomy' }).click()
    await screen.getByRole('button', { name: 'Unmake this row' }).click()
    await screen.getByRole('button', { name: 'Unmake it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/plant_anatomy:delete'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/plant_anatomy:delete')[0].body
    ).toEqual({
      table: 'plant_anatomy',
      key: { species_entity_id: 7 },
    })
  })
})

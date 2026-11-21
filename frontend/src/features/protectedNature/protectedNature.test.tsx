import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ProtectedNatureSection } from './ProtectedNatureSection'

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

const areas = {
  table: 'protected_areas',
  label: 'Protected areas',
  columns: [
    column('region_entity_id', 'integer', { owner: true, editable: false }),
    column('basis', 'choice', { options: ['law', 'faith'] }),
    column('strength', 'integer'),
  ],
  rows: [
    {
      key: { id: 5 },
      values: { region_entity_id: 7, basis: 'faith', strength: 60 },
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

describe('protection section', () => {
  beforeEach(() => resetApi())

  it('shows only the records of protection and strikes a protected land by its own lever', async () => {
    onApi('GET', '/api/records/7/rows', {
      node_id: 7,
      tables: [areas, tags],
      creatable: [areas, tags],
      names: {},
    })
    onApi('POST', '/api/actions/protected_area:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<ProtectedNatureSection nodeId={7} />)
    await expect
      .element(screen.getByText('Protection', { exact: true }))
      .toBeVisible()
    expect(
      screen.getByRole('button', { name: 'Open entity tags' }).query()
    ).toBeNull()
    await screen.getByRole('button', { name: 'Open protected areas' }).click()
    await screen.getByRole('button', { name: 'Unmake this row' }).click()
    await screen.getByRole('button', { name: 'Unmake it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/protected_area:delete'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/protected_area:delete')[0].body
    ).toEqual({
      table: 'protected_areas',
      key: { id: 5 },
    })
  })
})

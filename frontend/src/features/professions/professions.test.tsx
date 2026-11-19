import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ProfessionsSection } from './ProfessionsSection'

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
  table: 'professions_of_value',
  label: 'Professions of value',
  columns: [
    column('holder_node_id', 'integer', {
      owner: true,
      editable: false,
    }),
    column('axis', 'choice', { options: ['honour', 'piety'] }),
    column('gap', 'integer'),
  ],
  rows: [
    {
      key: { id: 3 },
      values: { holder_node_id: 7, axis: 'honour', gap: 40 },
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

describe('the professed values section', () => {
  beforeEach(() => resetApi())

  it('shows only its own records and strikes one by its own lever', async () => {
    onApi('GET', '/api/records/7/rows', {
      node_id: 7,
      tables: [rows, tags],
      creatable: [rows, tags],
      names: {},
    })
    onApi('POST', '/api/actions/profession_of_value:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<ProfessionsSection nodeId={7} />)
    await expect
      .element(screen.getByText('Professed values', { exact: true }))
      .toBeVisible()
    await expect
      .element(
        screen.getByRole('button', { name: 'Open professions of value' })
      )
      .toBeVisible()
    expect(
      screen.getByRole('button', { name: 'Open entity tags' }).query()
    ).toBeNull()
    await screen
      .getByRole('button', { name: 'Open professions of value' })
      .click()
    await screen.getByRole('button', { name: 'Unmake this row' }).click()
    await screen.getByRole('button', { name: 'Unmake it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/profession_of_value:delete'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/profession_of_value:delete')[0].body
    ).toEqual({
      table: 'professions_of_value',
      key: { id: 3 },
    })
  })
})

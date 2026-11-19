import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { NumbersSection } from './NumbersSection'

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
  table: 'population_policies',
  label: 'Population policies',
  columns: [
    column('holder_node_id', 'integer', {
      owner: true,
      editable: false,
    }),
    column('aim', 'choice', {
      options: ['grow', 'hold', 'shrink'],
    }),
    column('strength', 'integer'),
  ],
  rows: [
    {
      key: { id: 3 },
      values: { holder_node_id: 7, aim: 'grow', strength: 60 },
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

describe('numbers section', () => {
  beforeEach(() => resetApi())

  it('shows only the records of numbers and strikes them by their own lever', async () => {
    onApi('GET', '/api/records/7/rows', {
      node_id: 7,
      tables: [care, tags],
      creatable: [care, tags],
      names: {},
    })
    onApi('POST', '/api/actions/population_policy:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<NumbersSection nodeId={7} />)
    await expect
      .element(screen.getByText('Numbers', { exact: true }))
      .toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Open population policies' }))
      .toBeVisible()
    expect(
      screen.getByRole('button', { name: 'Open entity tags' }).query()
    ).toBeNull()
    await screen
      .getByRole('button', { name: 'Open population policies' })
      .click()
    await screen.getByRole('button', { name: 'Unmake this row' }).click()
    await screen.getByRole('button', { name: 'Unmake it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/population_policy:delete'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/population_policy:delete')[0].body
    ).toEqual({
      table: 'population_policies',
      key: { id: 3 },
    })
  })
})

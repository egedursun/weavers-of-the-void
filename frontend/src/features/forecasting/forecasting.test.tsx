import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ForecastingSection } from './ForecastingSection'

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
  table: 'observation_methods',
  label: 'Observation methods',
  columns: [
    column('people_entity_id', 'integer', {
      owner: true,
      editable: false,
    }),
    column('method', 'choice', { options: ['sight', 'model'] }),
    column('accuracy', 'integer'),
  ],
  rows: [
    {
      key: { id: 3 },
      values: { people_entity_id: 7, method: 'sight', accuracy: 20 },
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

describe('the forecasts and weather works section', () => {
  beforeEach(() => resetApi())

  it('shows only its own records and strikes one by its own lever', async () => {
    onApi('GET', '/api/records/7/rows', {
      node_id: 7,
      tables: [rows, tags],
      creatable: [rows, tags],
      names: {},
    })
    onApi('POST', '/api/actions/observation_method:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<ForecastingSection nodeId={7} />)
    await expect
      .element(screen.getByText('Forecasts and weather works', { exact: true }))
      .toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Open observation methods' }))
      .toBeVisible()
    expect(
      screen.getByRole('button', { name: 'Open entity tags' }).query()
    ).toBeNull()
    await screen
      .getByRole('button', { name: 'Open observation methods' })
      .click()
    await screen.getByRole('button', { name: 'Unmake this row' }).click()
    await screen.getByRole('button', { name: 'Unmake it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/observation_method:delete'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/observation_method:delete')[0].body
    ).toEqual({
      table: 'observation_methods',
      key: { id: 3 },
    })
  })
})

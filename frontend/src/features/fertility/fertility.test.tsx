import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { FertilitySection } from './FertilitySection'

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

const means = {
  table: 'fertility_means',
  label: 'Fertility means',
  columns: [
    column('people_entity_id', 'integer', { owner: true, editable: false }),
    column('means', 'choice', { options: ['prevention', 'surrogacy'] }),
    column('reliability', 'integer'),
  ],
  rows: [
    {
      key: { id: 5 },
      values: { people_entity_id: 7, means: 'prevention', reliability: 60 },
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

describe('fertility section', () => {
  beforeEach(() => resetApi())

  it('shows only the means of conception and strikes one by its own lever', async () => {
    onApi('GET', '/api/records/7/rows', {
      node_id: 7,
      tables: [means, tags],
      creatable: [means, tags],
      names: {},
    })
    onApi('POST', '/api/actions/fertility_means:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<FertilitySection nodeId={7} />)
    await expect
      .element(screen.getByText('Means of conception', { exact: true }))
      .toBeVisible()
    expect(
      screen.getByRole('button', { name: 'Open entity tags' }).query()
    ).toBeNull()
    await screen.getByRole('button', { name: 'Open fertility means' }).click()
    await screen.getByRole('button', { name: 'Unmake this row' }).click()
    await screen.getByRole('button', { name: 'Unmake it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/fertility_means:delete'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/fertility_means:delete')[0].body
    ).toEqual({
      table: 'fertility_means',
      key: { id: 5 },
    })
  })
})

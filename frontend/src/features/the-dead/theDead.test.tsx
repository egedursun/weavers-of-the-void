import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { TheDeadSection } from './TheDeadSection'

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
  table: 'death_work',
  label: 'Death work',
  columns: [
    column('people_entity_id', 'integer', {
      owner: true,
      editable: false,
    }),
    column('standing', 'choice', {
      options: ['honoured', 'plain', 'avoided'],
    }),
    column('purity', 'integer'),
  ],
  rows: [
    {
      key: { id: 3 },
      values: { people_entity_id: 7, standing: 'avoided', purity: 20 },
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

describe('the dead section', () => {
  beforeEach(() => resetApi())

  it('shows only the roles of the dead and strikes one by its own lever', async () => {
    onApi('GET', '/api/records/7/rows', {
      node_id: 7,
      tables: [roles, tags],
      creatable: [roles, tags],
      names: {},
    })
    onApi('POST', '/api/actions/death_work:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<TheDeadSection nodeId={7} />)
    await expect
      .element(screen.getByText('The dead', { exact: true }))
      .toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Open death work' }))
      .toBeVisible()
    expect(
      screen.getByRole('button', { name: 'Open entity tags' }).query()
    ).toBeNull()
    await screen.getByRole('button', { name: 'Open death work' }).click()
    await screen.getByRole('button', { name: 'Unmake this row' }).click()
    await screen.getByRole('button', { name: 'Unmake it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/death_work:delete'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/death_work:delete')[0].body).toEqual({
      table: 'death_work',
      key: { id: 3 },
    })
  })
})

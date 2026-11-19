import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { UnionsSection } from './UnionsSection'

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
  table: 'restraint_customs',
  label: 'Restraint customs',
  columns: [
    column('people_entity_id', 'integer', {
      owner: true,
      editable: false,
    }),
    column('role', 'choice', {
      options: ['clergy', 'ascetic', 'warrior'],
    }),
    column('strength', 'integer'),
  ],
  rows: [
    {
      key: { id: 3 },
      values: { people_entity_id: 7, role: 'clergy', strength: 70 },
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

describe('unions and birth section', () => {
  beforeEach(() => resetApi())

  it('shows only the records of unions and birth and strikes them by their own lever', async () => {
    onApi('GET', '/api/records/7/rows', {
      node_id: 7,
      tables: [care, tags],
      creatable: [care, tags],
      names: {},
    })
    onApi('POST', '/api/actions/restraint_custom:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<UnionsSection nodeId={7} />)
    await expect
      .element(screen.getByText('Unions and birth', { exact: true }))
      .toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Open restraint customs' }))
      .toBeVisible()
    expect(
      screen.getByRole('button', { name: 'Open entity tags' }).query()
    ).toBeNull()
    await screen.getByRole('button', { name: 'Open restraint customs' }).click()
    await screen.getByRole('button', { name: 'Unmake this row' }).click()
    await screen.getByRole('button', { name: 'Unmake it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/restraint_custom:delete'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/restraint_custom:delete')[0].body
    ).toEqual({
      table: 'restraint_customs',
      key: { id: 3 },
    })
  })
})

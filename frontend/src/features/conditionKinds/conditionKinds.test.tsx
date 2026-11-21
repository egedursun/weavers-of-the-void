import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ConditionKindsSection } from './ConditionKindsSection'

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

const kinds = {
  table: 'agentless_conditions',
  label: 'Agentless conditions',
  columns: [
    column('world_id', 'integer', { owner: true, editable: false }),
    column('cause', 'choice', { options: ['age', 'diet'] }),
    column('weight', 'integer'),
  ],
  rows: [
    {
      key: { id: 5 },
      values: { world_id: 7, cause: 'age', weight: 60 },
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

describe('condition kinds section', () => {
  beforeEach(() => resetApi())

  it('shows only the kinds of condition of a world and strikes one by its own lever', async () => {
    onApi('GET', '/api/records/7/rows', {
      node_id: 7,
      tables: [kinds, tags],
      creatable: [kinds, tags],
      names: {},
    })
    onApi('POST', '/api/actions/agentless_condition:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<ConditionKindsSection nodeId={7} />)
    await expect
      .element(
        screen.getByText('Conditions the body brings on', { exact: true })
      )
      .toBeVisible()
    expect(
      screen.getByRole('button', { name: 'Open entity tags' }).query()
    ).toBeNull()
    await screen
      .getByRole('button', { name: 'Open agentless conditions' })
      .click()
    await screen.getByRole('button', { name: 'Unmake this row' }).click()
    await screen.getByRole('button', { name: 'Unmake it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/agentless_condition:delete'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/agentless_condition:delete')[0].body
    ).toEqual({
      table: 'agentless_conditions',
      key: { id: 5 },
    })
  })
})

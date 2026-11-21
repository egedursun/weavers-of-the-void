import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { CreatureGroupsSection } from './CreatureGroupsSection'

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

const groups = {
  table: 'creature_groups',
  label: 'Creature groups',
  columns: [
    column('species_entity_id', 'integer', { owner: true, editable: false }),
    column('form', 'choice', { options: ['pack', 'herd'] }),
    column('size', 'integer'),
  ],
  rows: [
    {
      key: { id: 5 },
      values: { species_entity_id: 7, form: 'pack', size: 60 },
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

describe('creature groups section', () => {
  beforeEach(() => resetApi())

  it('shows only the creature groups and strikes one by its own lever', async () => {
    onApi('GET', '/api/records/7/rows', {
      node_id: 7,
      tables: [groups, tags],
      creatable: [groups, tags],
      names: {},
    })
    onApi('POST', '/api/actions/creature_group:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<CreatureGroupsSection nodeId={7} />)
    await expect
      .element(screen.getByText('Creature groups', { exact: true }))
      .toBeVisible()
    expect(
      screen.getByRole('button', { name: 'Open entity tags' }).query()
    ).toBeNull()
    await screen.getByRole('button', { name: 'Open creature groups' }).click()
    await screen.getByRole('button', { name: 'Unmake this row' }).click()
    await screen.getByRole('button', { name: 'Unmake it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/creature_group:delete'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/creature_group:delete')[0].body
    ).toEqual({
      table: 'creature_groups',
      key: { id: 5 },
    })
  })
})

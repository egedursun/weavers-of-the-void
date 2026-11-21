import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ArsenalSection } from './ArsenalSection'

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

const weapons = {
  table: 'mass_weapons',
  label: 'Mass weapons',
  columns: [
    column('holder_entity_id', 'integer', { owner: true, editable: false }),
    column('harm', 'choice', { options: ['blast', 'rite'] }),
    column('readiness', 'integer'),
  ],
  rows: [
    {
      key: { id: 5 },
      values: { holder_entity_id: 7, harm: 'rite', readiness: 60 },
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

describe('arsenal section', () => {
  beforeEach(() => resetApi())

  it('shows only the records of an arsenal and strikes a weapon by its own lever', async () => {
    onApi('GET', '/api/records/7/rows', {
      node_id: 7,
      tables: [weapons, tags],
      creatable: [weapons, tags],
      names: {},
    })
    onApi('POST', '/api/actions/mass_weapon:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<ArsenalSection nodeId={7} />)
    await expect
      .element(screen.getByText('Arsenal and remnants of war', { exact: true }))
      .toBeVisible()
    expect(
      screen.getByRole('button', { name: 'Open entity tags' }).query()
    ).toBeNull()
    await screen.getByRole('button', { name: 'Open mass weapons' }).click()
    await screen.getByRole('button', { name: 'Unmake this row' }).click()
    await screen.getByRole('button', { name: 'Unmake it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/mass_weapon:delete'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/mass_weapon:delete')[0].body).toEqual({
      table: 'mass_weapons',
      key: { id: 5 },
    })
  })
})

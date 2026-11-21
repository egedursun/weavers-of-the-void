import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { OccupationSection } from './OccupationSection'

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

const regimes = {
  table: 'occupation_regimes',
  label: 'Occupation regimes',
  columns: [
    column('occupier_entity_id', 'integer', { owner: true, editable: false }),
    column('rule', 'choice', { options: ['military', 'annexation'] }),
    column('tax_pct', 'integer'),
  ],
  rows: [
    {
      key: { id: 5 },
      values: { occupier_entity_id: 7, rule: 'military', tax_pct: 40 },
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

describe('occupation section', () => {
  beforeEach(() => resetApi())

  it('shows only the records of an occupation and strikes a regime by its own lever', async () => {
    onApi('GET', '/api/records/7/rows', {
      node_id: 7,
      tables: [regimes, tags],
      creatable: [regimes, tags],
      names: {},
    })
    onApi('POST', '/api/actions/occupation_regime:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<OccupationSection nodeId={7} />)
    await expect
      .element(screen.getByText('Occupation', { exact: true }))
      .toBeVisible()
    expect(
      screen.getByRole('button', { name: 'Open entity tags' }).query()
    ).toBeNull()
    await screen
      .getByRole('button', { name: 'Open occupation regimes' })
      .click()
    await screen.getByRole('button', { name: 'Unmake this row' }).click()
    await screen.getByRole('button', { name: 'Unmake it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/occupation_regime:delete'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/occupation_regime:delete')[0].body
    ).toEqual({
      table: 'occupation_regimes',
      key: { id: 5 },
    })
  })
})

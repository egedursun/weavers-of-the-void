import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { DivineConceptionsSection } from './DivineConceptionsSection'

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

const conceptions = {
  table: 'divine_conceptions',
  label: 'Divine conceptions',
  columns: [
    column('cult_entity_id', 'integer', { owner: true, editable: false }),
    column('count', 'choice', { options: ['one', 'many'] }),
    column('strain', 'integer'),
  ],
  rows: [
    {
      key: { cult_entity_id: 7 },
      values: { cult_entity_id: 7, count: 'one', strain: 60 },
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

describe('divine conceptions section', () => {
  beforeEach(() => resetApi())

  it('shows only how a faith holds the divine and strikes it by its own lever', async () => {
    onApi('GET', '/api/records/7/rows', {
      node_id: 7,
      tables: [conceptions, tags],
      creatable: [conceptions, tags],
      names: {},
    })
    onApi('POST', '/api/actions/divine_conception:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<DivineConceptionsSection nodeId={7} />)
    await expect
      .element(screen.getByText('Conception of the divine', { exact: true }))
      .toBeVisible()
    expect(
      screen.getByRole('button', { name: 'Open entity tags' }).query()
    ).toBeNull()
    await screen
      .getByRole('button', { name: 'Open divine conceptions' })
      .click()
    await screen.getByRole('button', { name: 'Unmake this row' }).click()
    await screen.getByRole('button', { name: 'Unmake it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/divine_conception:delete'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/divine_conception:delete')[0].body
    ).toEqual({
      table: 'divine_conceptions',
      key: { cult_entity_id: 7 },
    })
  })
})

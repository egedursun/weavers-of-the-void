import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MoneyPolicySection } from './MoneyPolicySection'

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

const authorities = {
  table: 'monetary_authorities',
  label: 'Monetary authorities',
  columns: [
    column('holder_node_id', 'integer', { owner: true, editable: false }),
    column('aim', 'choice', { options: ['stable_value', 'peg'] }),
    column('rate', 'integer'),
  ],
  rows: [
    {
      key: { id: 5 },
      values: { holder_node_id: 7, aim: 'stable_value', rate: 60 },
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

describe('money section', () => {
  beforeEach(() => resetApi())

  it('shows only the records of money and strikes an authority by its own lever', async () => {
    onApi('GET', '/api/records/7/rows', {
      node_id: 7,
      tables: [authorities, tags],
      creatable: [authorities, tags],
      names: {},
    })
    onApi('POST', '/api/actions/monetary_authority:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<MoneyPolicySection nodeId={7} />)
    await expect
      .element(screen.getByText('Money', { exact: true }))
      .toBeVisible()
    expect(
      screen.getByRole('button', { name: 'Open entity tags' }).query()
    ).toBeNull()
    await screen
      .getByRole('button', { name: 'Open monetary authorities' })
      .click()
    await screen.getByRole('button', { name: 'Unmake this row' }).click()
    await screen.getByRole('button', { name: 'Unmake it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/monetary_authority:delete'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/monetary_authority:delete')[0].body
    ).toEqual({
      table: 'monetary_authorities',
      key: { id: 5 },
    })
  })
})

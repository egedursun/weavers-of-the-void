import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { SecuritiesSection } from './SecuritiesSection'

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

const holdings = {
  table: 'security_holdings',
  label: 'Security holdings',
  columns: [
    column('holder_node_id', 'integer', { owner: true, editable: false }),
    column('amount', 'integer', { options: [] }),
    column('on_margin', 'integer'),
  ],
  rows: [
    {
      key: { id: 5 },
      values: { holder_node_id: 7, amount: 10, on_margin: 60 },
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

describe('securities section', () => {
  beforeEach(() => resetApi())

  it('shows only the records of securities and strikes a holding by its own lever', async () => {
    onApi('GET', '/api/records/7/rows', {
      node_id: 7,
      tables: [holdings, tags],
      creatable: [holdings, tags],
      names: {},
    })
    onApi('POST', '/api/actions/security_holding:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<SecuritiesSection nodeId={7} />)
    await expect
      .element(screen.getByText('Securities', { exact: true }))
      .toBeVisible()
    expect(
      screen.getByRole('button', { name: 'Open entity tags' }).query()
    ).toBeNull()
    await screen.getByRole('button', { name: 'Open security holdings' }).click()
    await screen.getByRole('button', { name: 'Unmake this row' }).click()
    await screen.getByRole('button', { name: 'Unmake it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/security_holding:delete'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/security_holding:delete')[0].body
    ).toEqual({
      table: 'security_holdings',
      key: { id: 5 },
    })
  })
})

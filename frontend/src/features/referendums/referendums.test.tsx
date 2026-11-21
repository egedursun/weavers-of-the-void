import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ReferendumsSection } from './ReferendumsSection'

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

const disputes = {
  table: 'referendums',
  label: 'Referendums',
  columns: [
    column('holder_node_id', 'integer', { owner: true, editable: false }),
    column('result', 'choice', {
      options: ['pending', 'passed', 'failed', 'void'],
    }),
    column('yes_pct', 'integer'),
  ],
  rows: [
    {
      key: { id: 5 },
      values: { holder_node_id: 7, result: 'pending', yes_pct: 60 },
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

describe('votes section', () => {
  beforeEach(() => resetApi())

  it('shows only the records of votes, decides one and strikes it by its own lever', async () => {
    onApi('GET', '/api/records/7/rows', {
      node_id: 7,
      tables: [disputes, tags],
      creatable: [disputes, tags],
      names: {},
    })
    onApi('POST', '/api/actions/referendum:delete', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/referendum:decide', ACCEPTED_ACTION)
    const { screen } = await renderApp(<ReferendumsSection nodeId={7} />)
    await expect
      .element(screen.getByText('Votes', { exact: true }))
      .toBeVisible()
    expect(
      screen.getByRole('button', { name: 'Open entity tags' }).query()
    ).toBeNull()
    await screen.getByRole('button', { name: 'Open referendums' }).click()
    await screen.getByRole('button', { name: 'Decide this vote' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/referendum:decide'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/referendum:decide')[0].body).toEqual({
      record_id: 5,
    })
    await screen.getByRole('button', { name: 'Unmake this row' }).click()
    await screen.getByRole('button', { name: 'Unmake it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/referendum:delete'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/referendum:delete')[0].body).toEqual({
      table: 'referendums',
      key: { id: 5 },
    })
  })
})

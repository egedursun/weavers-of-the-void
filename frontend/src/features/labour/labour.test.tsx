import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { LabourSection } from './LabourSection'

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
  table: 'labour_disputes',
  label: 'Labour disputes',
  columns: [
    column('body_node_id', 'integer', { owner: true, editable: false }),
    column('outcome', 'choice', {
      options: ['ongoing', 'won', 'lost', 'settled'],
    }),
    column('workers_out', 'integer'),
  ],
  rows: [
    {
      key: { id: 5 },
      values: { body_node_id: 7, outcome: 'ongoing', workers_out: 60 },
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

describe('labour section', () => {
  beforeEach(() => resetApi())

  it('shows only the records of labour, settles a dispute and strikes it by its own lever', async () => {
    onApi('GET', '/api/records/7/rows', {
      node_id: 7,
      tables: [disputes, tags],
      creatable: [disputes, tags],
      names: {},
    })
    onApi('POST', '/api/actions/labour_dispute:delete', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/labour_dispute:end', ACCEPTED_ACTION)
    const { screen } = await renderApp(<LabourSection nodeId={7} />)
    await expect
      .element(screen.getByText('Labour', { exact: true }))
      .toBeVisible()
    expect(
      screen.getByRole('button', { name: 'Open entity tags' }).query()
    ).toBeNull()
    await screen.getByRole('button', { name: 'Open labour disputes' }).click()
    await screen.getByRole('button', { name: 'Settle this dispute' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/labour_dispute:end'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/labour_dispute:end')[0].body).toEqual({
      record_id: 5,
    })
    await screen.getByRole('button', { name: 'Unmake this row' }).click()
    await screen.getByRole('button', { name: 'Unmake it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/labour_dispute:delete'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/labour_dispute:delete')[0].body
    ).toEqual({
      table: 'labour_disputes',
      key: { id: 5 },
    })
  })
})

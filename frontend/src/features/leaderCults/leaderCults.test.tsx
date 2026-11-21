import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { LeaderCultsSection } from './LeaderCultsSection'

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

const cults = {
  table: 'leader_cults',
  label: 'Leader cults',
  columns: [
    column('leader_node_id', 'integer', { owner: true, editable: false }),
    column('fate', 'choice', { options: ['living', 'faded'] }),
    column('intensity', 'integer'),
  ],
  rows: [
    {
      key: { id: 5 },
      values: { leader_node_id: 7, fate: 'living', intensity: 60 },
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

describe('leader cult section', () => {
  beforeEach(() => resetApi())

  it('shows only the records of a cult and strikes it by its own lever', async () => {
    onApi('GET', '/api/records/7/rows', {
      node_id: 7,
      tables: [cults, tags],
      creatable: [cults, tags],
      names: {},
    })
    onApi('POST', '/api/actions/leader_cult:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<LeaderCultsSection nodeId={7} />)
    await expect
      .element(screen.getByText('Cult of a leader', { exact: true }))
      .toBeVisible()
    expect(
      screen.getByRole('button', { name: 'Open entity tags' }).query()
    ).toBeNull()
    await screen.getByRole('button', { name: 'Open leader cults' }).click()
    await screen.getByRole('button', { name: 'Unmake this row' }).click()
    await screen.getByRole('button', { name: 'Unmake it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/leader_cult:delete'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/leader_cult:delete')[0].body).toEqual({
      table: 'leader_cults',
      key: { id: 5 },
    })
  })
})

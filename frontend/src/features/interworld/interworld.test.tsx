import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { InterworldSection } from './InterworldSection'

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

const campaigns = {
  table: 'interworld_campaigns',
  label: 'Interworld campaigns',
  columns: [
    column('attacker_entity_id', 'integer', { owner: true, editable: false }),
    column('stage', 'choice', { options: ['transit', 'holding'] }),
    column('supply', 'integer'),
  ],
  rows: [
    {
      key: { id: 5 },
      values: { attacker_entity_id: 7, stage: 'transit', supply: 60 },
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

describe('between worlds section', () => {
  beforeEach(() => resetApi())

  it('shows only the records between worlds and strikes a campaign by its own lever', async () => {
    onApi('GET', '/api/records/7/rows', {
      node_id: 7,
      tables: [campaigns, tags],
      creatable: [campaigns, tags],
      names: {},
    })
    onApi('POST', '/api/actions/interworld_campaign:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<InterworldSection nodeId={7} />)
    await expect
      .element(screen.getByText('Between worlds', { exact: true }))
      .toBeVisible()
    expect(
      screen.getByRole('button', { name: 'Open entity tags' }).query()
    ).toBeNull()
    await screen
      .getByRole('button', { name: 'Open interworld campaigns' })
      .click()
    await screen.getByRole('button', { name: 'Unmake this row' }).click()
    await screen.getByRole('button', { name: 'Unmake it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/interworld_campaign:delete'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/interworld_campaign:delete')[0].body
    ).toEqual({
      table: 'interworld_campaigns',
      key: { id: 5 },
    })
  })
})

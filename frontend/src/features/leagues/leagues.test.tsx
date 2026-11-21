import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { LeaguesSection } from './LeaguesSection'

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

const members = {
  table: 'league_members',
  label: 'League members',
  columns: [
    column('polity_entity_id', 'integer', { owner: true, editable: false }),
    column('standing', 'choice', { options: ['founder', 'member'] }),
    column('dues_paid', 'integer'),
  ],
  rows: [
    {
      key: { id: 5 },
      values: { polity_entity_id: 7, standing: 'member', dues_paid: 60 },
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

describe('leagues section', () => {
  beforeEach(() => resetApi())

  it('shows only the records of leagues and strikes a member by its own lever', async () => {
    onApi('GET', '/api/records/7/rows', {
      node_id: 7,
      tables: [members, tags],
      creatable: [members, tags],
      names: {},
    })
    onApi('POST', '/api/actions/league_member:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<LeaguesSection nodeId={7} />)
    await expect
      .element(screen.getByText('Leagues', { exact: true }))
      .toBeVisible()
    expect(
      screen.getByRole('button', { name: 'Open entity tags' }).query()
    ).toBeNull()
    await screen.getByRole('button', { name: 'Open league members' }).click()
    await screen.getByRole('button', { name: 'Unmake this row' }).click()
    await screen.getByRole('button', { name: 'Unmake it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/league_member:delete'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/league_member:delete')[0].body
    ).toEqual({
      table: 'league_members',
      key: { id: 5 },
    })
  })

  it('dissolves a league from its own drawer and keeps founding closed with its reason', async () => {
    onApi('GET', '/api/records/7/rows', {
      node_id: 7,
      tables: [],
      creatable: [],
      names: {},
    })
    onApi('GET', '/api/names', [
      {
        id: 7,
        kind: 'entity',
        type: 'league',
        name: 'the league of the hills',
        status: 'canon',
      },
    ])
    onApi('POST', '/api/actions/league:dissolve', ACCEPTED_ACTION)
    const { screen } = await renderApp(<LeaguesSection nodeId={7} />)
    await expect
      .element(screen.getByRole('button', { name: 'Found it' }))
      .toBeDisabled()
    await screen.getByRole('button', { name: 'Dissolve this league' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/league:dissolve'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/league:dissolve')[0].body).toEqual({
      league_id: 7,
    })
  })
})

import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { CityRulesSection } from './CityRulesSection'

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

const cities = {
  table: 'conurbations',
  label: 'Conurbations',
  columns: [
    column('core_entity_id', 'integer', { owner: true, editable: false }),
    column('governance', 'choice', {
      options: ['one_council', 'ruled_by_core'],
    }),
    column('joined_epoch', 'integer'),
  ],
  rows: [
    {
      key: { id: 5 },
      values: {
        core_entity_id: 7,
        split_epoch: null,
        governance: 'one_council',
        joined_epoch: 3,
      },
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

describe('city rules section', () => {
  beforeEach(() => resetApi())

  it('shows only the records of a city, splits it and strikes it by its own lever', async () => {
    onApi('GET', '/api/records/7/rows', {
      node_id: 7,
      tables: [cities, tags],
      creatable: [cities, tags],
      names: {},
    })
    onApi('POST', '/api/actions/conurbation:delete', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/conurbation:split', ACCEPTED_ACTION)
    const { screen } = await renderApp(<CityRulesSection nodeId={7} />)
    await expect
      .element(screen.getByText('City rules and services', { exact: true }))
      .toBeVisible()
    expect(
      screen.getByRole('button', { name: 'Open entity tags' }).query()
    ).toBeNull()
    await screen.getByRole('button', { name: 'Open conurbations' }).click()
    await screen
      .getByRole('button', { name: 'Split it into its settlements' })
      .click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/conurbation:split'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/conurbation:split')[0].body).toEqual({
      record_id: 5,
    })
    await screen.getByRole('button', { name: 'Unmake this row' }).click()
    await screen.getByRole('button', { name: 'Unmake it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/conurbation:delete'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/conurbation:delete')[0].body).toEqual({
      table: 'conurbations',
      key: { id: 5 },
    })
  })
})

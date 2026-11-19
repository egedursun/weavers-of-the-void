import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { DailyLifeSection } from './DailyLifeSection'

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

const care = {
  table: 'care_customs',
  label: 'Care customs',
  columns: [
    column('people_entity_id', 'integer', {
      primary: true,
      owner: true,
      editable: false,
    }),
    column('wash_frequency', 'choice', {
      options: ['none', 'by_rite', 'seasonal', 'weekly', 'daily'],
    }),
    column('cleanliness', 'integer'),
  ],
  rows: [
    {
      key: { people_entity_id: 7 },
      values: { people_entity_id: 7, wash_frequency: 'daily', cleanliness: 70 },
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

describe('daily life section', () => {
  beforeEach(() => resetApi())

  it('shows only the records of daily life and strikes them by their own lever', async () => {
    onApi('GET', '/api/records/7/rows', {
      node_id: 7,
      tables: [care, tags],
      creatable: [care, tags],
      names: {},
    })
    onApi('POST', '/api/actions/care_custom:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<DailyLifeSection nodeId={7} />)
    await expect.element(screen.getByText('Daily life')).toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Open care customs' }))
      .toBeVisible()
    expect(
      screen.getByRole('button', { name: 'Open entity tags' }).query()
    ).toBeNull()
    await screen.getByRole('button', { name: 'Open care customs' }).click()
    await screen.getByRole('button', { name: 'Unmake this row' }).click()
    await screen.getByRole('button', { name: 'Unmake it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/care_custom:delete'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/care_custom:delete')[0].body).toEqual({
      table: 'care_customs',
      key: { people_entity_id: 7 },
    })
  })
})

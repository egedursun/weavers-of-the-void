import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MoodSection } from './MoodSection'

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

const moods = {
  table: 'feeling_spread',
  label: 'Feeling spread',
  columns: [
    column('settlement_entity_id', 'integer', { owner: true, editable: false }),
    column('leading', 'choice', { options: ['joy', 'fear'] }),
    column('updated_epoch', 'integer'),
  ],
  rows: [
    {
      key: { id: 5 },
      values: { settlement_entity_id: 7, leading: 'fear', updated_epoch: 3 },
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

describe('mood section', () => {
  beforeEach(() => resetApi())

  it('shows only the mood of a place and clears it by its own lever', async () => {
    onApi('GET', '/api/records/7/rows', {
      node_id: 7,
      tables: [moods, tags],
      creatable: [moods, tags],
      names: {},
    })
    onApi('POST', '/api/actions/feeling_spread:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<MoodSection nodeId={7} />)
    await expect
      .element(screen.getByText('Mood', { exact: true }))
      .toBeVisible()
    expect(
      screen.getByRole('button', { name: 'Open entity tags' }).query()
    ).toBeNull()
    await screen.getByRole('button', { name: 'Open feeling spread' }).click()
    await screen.getByRole('button', { name: 'Unmake this row' }).click()
    await screen.getByRole('button', { name: 'Unmake it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/feeling_spread:delete'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/feeling_spread:delete')[0].body
    ).toEqual({
      table: 'feeling_spread',
      key: { id: 5 },
    })
  })
})

import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { SpeechSection } from './SpeechSection'

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
  table: 'speeches',
  label: 'Speeches',
  columns: [
    column('speaker_node_id', 'integer', {
      owner: true,
      editable: false,
    }),
    column('venue', 'choice', {
      options: ['assembly', 'square', 'temple'],
    }),
    column('skill', 'integer'),
  ],
  rows: [
    {
      key: { id: 3 },
      values: { speaker_node_id: 7, venue: 'square', skill: 60 },
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

describe('speech section', () => {
  beforeEach(() => resetApi())

  it('shows only the records of speech and strikes them by their own lever', async () => {
    onApi('GET', '/api/records/7/rows', {
      node_id: 7,
      tables: [care, tags],
      creatable: [care, tags],
      names: {},
    })
    onApi('POST', '/api/actions/speech:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<SpeechSection nodeId={7} />)
    await expect
      .element(screen.getByText('Humour and speech', { exact: true }))
      .toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Open speeches' }))
      .toBeVisible()
    expect(
      screen.getByRole('button', { name: 'Open entity tags' }).query()
    ).toBeNull()
    await screen.getByRole('button', { name: 'Open speeches' }).click()
    await screen.getByRole('button', { name: 'Unmake this row' }).click()
    await screen.getByRole('button', { name: 'Unmake it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/speech:delete'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/speech:delete')[0].body).toEqual({
      table: 'speeches',
      key: { id: 3 },
    })
  })
})
